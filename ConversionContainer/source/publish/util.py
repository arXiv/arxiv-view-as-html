import os

def rename (site_dir: str, submission_id: int, paper_idv: str):
    doc_dir = os.path.join(site_dir, paper_idv)
    # Rename directory
    os.rename(os.path.join(site_dir, str(submission_id)), doc_dir)
    # Rename html file
    os.rename(os.path.join(doc_dir, f'{submission_id}.html'), 
              os.path.join(doc_dir, f'{paper_idv}.html'))