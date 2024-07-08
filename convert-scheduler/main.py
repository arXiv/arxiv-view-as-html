from typing import Optional, List
import random
from json import loads
import logging
import argparse
import asyncio
from asyncio.queues import Queue
import aiohttp
from datetime import datetime, timedelta
import pytz
import time
from pydantic import BaseModel

from sqlalchemy.sql import select
from sqlalchemy.sql.expression import func

from arxiv.db.models import Metadata, DBLaTeXMLDocuments
from arxiv.db import get_db, SessionLocal

from config import settings

logger = logging.getLogger("convert_scheduler_log")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(settings.LOG_PATH)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

data_logger = logging.getLogger("time_logger")
data_logger.setLevel(logging.DEBUG)
time_fh = logging.FileHandler(settings.DATA_LOG_PATH)
time_fh.setLevel(logging.DEBUG)
data_logger.addHandler(time_fh)
data_logger.info('paper_idv, convert_time')
start_time = time.time()

class ConvertData (BaseModel):
    paper_id: str
    version: int
    single_file: bool
    is_latest: bool

class ConvertDataIterator:

    def __init__ (self, starting_meta_id: Optional[int] = None, latexml_version: Optional[str] = None):
        self.latexml_version = latexml_version
        if starting_meta_id is None:
            with get_db() as session:
                self.current_meta_id = session.scalar(
                    select(func.max(Metadata.metadata_id))
                )
        else:
            self.current_meta_id = starting_meta_id
        print (self.current_meta_id)
        
    def __iter__ (self) -> 'ConvertDataIterator':
        return self
    
    def __next__ (self) -> ConvertData:
        with get_db() as session:
            while self.current_meta_id >= 0:
                try:
                    item = session.execute (
                        select(Metadata.paper_id, Metadata.version, Metadata.source_flags, Metadata.source_format, Metadata.is_withdrawn, Metadata.is_current)
                        .filter(Metadata.metadata_id == self.current_meta_id)
                    ).first()
                    if item is None:
                        logger.info(f'No result for {self.current_meta_id}')
                        continue
                    paper_id, version, source_flags, source_format, is_withdrawn, is_current = item._t
                    if is_withdrawn or not 'tex' in source_format:
                        logger.info(f'Not converting {self.current_meta_id} - withdrawn or no TeX source')
                        continue
                    if self.latexml_version:
                        latexml_conversion = session.execute(
                            select(DBLaTeXMLDocuments.conversion_status, DBLaTeXMLDocuments.latexml_version, DBLaTeXMLDocuments.publish_dt)
                            .filter(DBLaTeXMLDocuments.paper_id == paper_id)
                            .filter(DBLaTeXMLDocuments.document_version == version)
                        ).first()
                        if latexml_conversion:
                            conversion_status, latexml_version, publish_dt = latexml_conversion._t
                            if conversion_status == 1 and latexml_version == self.latexml_version and publish_dt is not None:
                                logger.info(f'Not converting {self.current_meta_id} - already an existing conversion')
                                continue
                    return ConvertData(
                        paper_id=paper_id,
                        version=version,
                        single_file=(('1' in source_flags) if source_flags else False),
                        is_latest=bool(is_current)
                    )
                except Exception as e:
                    print(f'Error converting {self.current_meta_id} with {e}')
                    logger.warning(f'Error converting {self.current_meta_id} with {e}')
                    continue
                finally:
                    self.current_meta_id -= 1
        raise StopIteration

async def scheduler(args):
    count = 1
    async def worker (url: str, intervals: List[List[int]], override_days: List[int], queue: Queue, args):
        print (f"STARTING WORKER {url}")
        async with aiohttp.ClientSession() as session:
            while True:
                now = datetime.now(tz=pytz.timezone('US/Eastern'))
                min_next_hour = 25
                if intervals and not now.weekday() in override_days:
                    in_interval = False
                    for interval in intervals:
                        if now.hour > interval[0] and now.hour < interval[1]:
                            in_interval = True
                            break
                        if now.hour < interval[0] and interval[0] < min_next_hour:
                            min_next_hour = interval[0]
                else:
                    in_interval=True
                
                if in_interval:
                    convert_data: ConvertData = await queue.get()

                    if convert_data is None:
                        queue.task_done()
                        break
                    
                    print (f'SENDING {convert_data} to {url}')
                    logger.info(f'SENDING {convert_data} to {url}')
                    if not args.dry_run:
                        start = time.time()
                        try:
                            async with session.post(url, json=convert_data.json(), timeout=500) as response:
                                text = await response.text()
                        except Exception as e:
                            print (f"Encountered exception {e}")
                            ...
                        end = time.time()
                        data_logger.info(f'{convert_data.paper_id}v{convert_data.version}, {end-start}')        
                    else:
                        await asyncio.sleep(random.randint(1, 5))
                    queue.task_done()
                else:
                    await asyncio.sleep((now.replace(hour=min_next_hour, minute=0, second=0)-now).total_seconds())

    iterator = ConvertDataIterator(args.start_meta_id, args.latexml_sha)

    with open('workers_schedules.json') as f:
        workers_schedules = loads(f.read())

    max_q_size = sum(map(lambda x: x['concurrency'], workers_schedules))
    queue = Queue(maxsize=max_q_size)

    workers = []
    for item in workers_schedules:
        workers.extend([asyncio.create_task(worker('http://' + item['url'] + settings.CONVERT_PATH, 
                                          item['intervals'],
                                          item['override_days'],
                                          queue, 
                                          args)) for _ in range(item['concurrency'])])
    
    while True or (count > 300 and args.timing_test):
        if queue.qsize() < max_q_size:
            try:
                conv_data = next(iterator)
                await queue.put(conv_data)
            except StopIteration:
                break
        else:
            await asyncio.sleep(1)
        count += 1

    await queue.join()

    for _ in range(max_q_size):
        await queue.put(None)

    for w in workers:
        await w

async def main(args):
    await scheduler(args)

if __name__=='__main__':
    parser = argparse.ArgumentParser(
        description='Convert entire arXiv corpus to HTML by scheduling conversions on CIT machines',
    )
    parser.add_argument('-n', '--dry-run', 
                        action='store_true',
                        help='Log requests sent without sending them')
    parser.add_argument('-s', '--start-meta-id',
                        type=int, default=None,
                        help="An optional metadata id to start at (counting down from)")
    parser.add_argument('-t', '--timing-test',
                        action='store_true',
                        help="If this is set, we will convert 1000 papers and time them")
    parser.add_argument('-l', '--latexml-sha',
                        type=str, default=None,
                        help="If there already exists a conversion with this version, skip")
    args = parser.parse_args()

    asyncio.run(main(args))
    # import requests
    # import json
    # res = requests.post('http://127.0.0.1:8000/process-full-corpus', json=json.dumps({
    #     'paper_id': '1706.03762',
    #     'version': 6,
    #     'single_file': False,
    #     'is_latest': False
    # }))
    # print (res.status_code)