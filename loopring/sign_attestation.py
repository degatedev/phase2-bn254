import subprocess

# sign using keybase
subprocess.check_call(["keybase", "pgp", "sign", "--clearsign", "-i", "attestation.txt", "-o", "signed_attestation.txt"])
