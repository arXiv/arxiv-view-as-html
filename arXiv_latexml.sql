CREATE TABLE arXiv_latexml (
    document_id INTEGER NOT NULL,
    document_version INTEGER NOT NULL,
    conversion_status INTEGER NOT NULL,
    conversion_start_time DATETIME NOT NULL,
    conversion_end_time DATETIME,
    latexml_version VARCHAR(10),

    PRIMARY KEY (document_id, document_version)
    -- FOREIGN KEY (document_id) 
    --     REFERENCES arXiv_documents (document_id)
);