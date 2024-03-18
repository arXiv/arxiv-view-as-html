def do_latexml(main_fpath: str, out_dpath: str, sub_id: str, is_submission: bool) -> Optional[List[str]]:
    """
    Runs latexml on the .tex file at main_fpath and
    outputs the html at out_fpath.

    Parameters
    ----------
    main_fpath : str
        Main .tex file path
    out_dpath : str
        Output directory file path
    sub_id: str
        submission id of the article
    """
    LATEXML_URL_BASE = current_app.config['LATEXML_URL_BASE']
    latexml_config = ["latexmlc",
                      "--preload=[nobibtex,ids,localrawstyles,mathlexemes,magnify=2,zoomout=2,tokenlimit=99999999,iflimit=1499999,absorblimit=1299999,pushbacklimit=599999]latexml.sty",
                      "--path=/opt/arxmliv-bindings/bindings",
                      "--path=/opt/arxmliv-bindings/supported_originals",
                      "--pmml", "--cmml", "--mathtex",
                      "--timeout=500",
                      "--nodefaultresources",
                      "--css=https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
                      f"--css={LATEXML_URL_BASE}/css/ar5iv_0.7.4.min.css",
                      f"--css={LATEXML_URL_BASE}/css/latexml_styles.css",
                      "--javascript=https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
                      "--javascript=https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.3.3/html2canvas.min.js",
                      f"--javascript={LATEXML_URL_BASE}/js/addons.js",
                      f"--javascript={LATEXML_URL_BASE}/js/feedbackOverlay.js",
                      "--navigationtoc=context",
                      f"--source={main_fpath}", f"--dest={out_dpath}/{sub_id}.html"]
    completed_process = subprocess.run(
        latexml_config,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        text=True,
        timeout=500)
    errpath = os.path.join(os.getcwd(), f"{sub_id}_stdout.txt")
    with open(errpath, "w") as f:
        f.write(completed_process.stdout)
    try:
        if is_submission:
            bucket = get_google_storage_client().bucket(current_app.config['QA_BUCKET_SUB'])
        else:
            bucket = get_google_storage_client().bucket(current_app.config['QA_BUCKET_DOC'])
        errblob = bucket.blob(f"{sub_id}_stdout.txt")
        errblob.upload_from_filename(f"{sub_id}_stdout.txt")
    except Exception as exc:
        raise GCPBlobError(
            f"Uploading {sub_id}_stdout.txt to {current_app.config['QA_BUCKET_SUB'] if is_submission else current_app.config['QA_BUCKET_DOC']} failed in do_latexml") from exc
    os.remove(errpath)
    return _list_missing_packages(completed_process.stdout)