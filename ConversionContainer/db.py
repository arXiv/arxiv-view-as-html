"""
Description: This file contains methods for hypothetically communicating with
with the database. The only reason we would need to do this is to update a 
currently nonexistent field indicating the status of the html processing. Right
now, if there is not tar in the html bucket for a given submission id, that 
could mean that it is either still processing or failed. 
"""

# Set the field to indicate the processing
# finished successfully
def write_success(submission_id):
    pass

# Set the field to indicate that LaTeXML
# is still processing the source
def write_in_progress(submission_id):
    pass

# Use this method in catch blocks to
# indicate that the processing failed
# unrecoverably
def write_failure(submission_id):
    pass
