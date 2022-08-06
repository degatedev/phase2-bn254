import os
import sys
import shutil
import subprocess
import config
import time
from zipfile import ZipFile, ZIP_DEFLATED

def mpc_contribute(params_file, entropy, logfile, contribute_beacon):
    if contribute_beacon:
        subprocess.check_call([config.phase2_repo_path + "phase2/target/release/beacon", params_file, params_file], stdout=logfile)
    else:
        subprocess.check_call([config.phase2_repo_path + "phase2/target/release/contribute", params_file, entropy, params_file], stdout=logfile)

def print_and_log(logfile, text):
    print(text)
    logfile.write(text + "\n")
    logfile.flush()

def print_log(logfile, text):
    logfile.write(text + "\n")
    logfile.flush()

if __name__ == "__main__":
    contribute_beacon = False
    if len(sys.argv) == 2:
        contribute_beacon = (sys.argv[1] == "beacon")

    circuits = config.get_circuits()
    print("Contributing to " + str(len(circuits)) + " circuits.")
    if contribute_beacon:
        entropy = ""
    else:
        entropy = sys.argv[2]

    index = config.find_latest_contribution_index()

    start_contribution = config.get_zip_filename(index)
    new_contribution = config.get_zip_filename(index+1)

    attestation = open("attestation.txt", "w")

    with open('template_contribution_details.txt') as f:
        contribution_details_template = f.read()
        attestation.write(contribution_details_template)
    attestation.write("\n\n!!!Don't modify anything from this point on!!!\n")
    attestation.write("----------------------------------------------\n")

    if contribute_beacon:
        print_and_log(attestation, "Contributing the beacon!")

    # calculate the hash of the contribution we start from
    start_hash = config.hash_file(start_contribution)

    # add log to trusted-setup.log
    trustedlog = open("/opt/trustmount/trusted-setup.log", "a")
    time_to_trustedlog = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if sys.argv[1] == "beacon":
        print_and_log(attestation, "\nStarting from contribution " + str(index) + " with SHA256 hash " + str(start_hash) + " (please check if this is correct)\n")
    elif sys.argv[1] == start_hash:
        print_log(trustedlog, time_to_trustedlog + " Starting from contribution " + str(index) + " with SHA256 hash " + str(start_hash) + " (check result is correct, this process takes a long time, about 20 hours)")
    else:
        print_log(trustedlog, time_to_trustedlog +  " Starting from contribution " + str(index) + " with SHA256 hash " + str(start_hash) + " (check result is incorrect, please contact the coordinator)")
        trustedlog.close()
        os._exit(1)

    start = time.time()
    try:
        with ZipFile(start_contribution, 'r') as from_file, ZipFile(new_contribution, 'w', ZIP_DEFLATED) as to_file:
            for idx, circuit in enumerate(circuits):
                print_and_log(attestation, "Contributing to circuit " + str(idx+1) + "/" + str(len(circuits)) + "...")

                params = config.get_params_filename(circuit)
                # extract the params file from the downloaded file
                from_file.extract(os.path.basename(params), os.path.dirname(params))
                # contribute
                mpc_contribute(params, entropy, attestation, contribute_beacon)
                # add it to the new zip file
                to_file.write(params, os.path.basename(params))
                # delete the file
                os.remove(params)
                # delete the empty params folder
                os.rmdir(os.path.dirname(params))
    except Exception as e:
        print(e)
        print_and_log(attestation, "\nAn error occured while contributing! Please try again!\n")
        os.remove(new_contribution)
        params = config.get_params_filename(circuits[0])
        shutil.rmtree(os.path.dirname(params))
        exit(1)

    # calculate the hash of the contribution we start from
    end_hash = config.hash_file(new_contribution)

    print_and_log(attestation, "\nDone! Thank you for contributing as participant " + str(index+1) + "!")
    print_and_log(attestation, "Your contribution has SHA256 hash " + str(end_hash))
    print_and_log(attestation, "Please upload '" + new_contribution + "'.")
    print_and_log(attestation, "Also please fill out 'attestation.txt' and sign it by running 'keybase pgp sign --clearsign -i attestation.txt -o signed_attestation.txt' and send us 'signed_attestation.txt'.")

    end = time.time()
    print_and_log(attestation, "Contributing took " + str(end - start) + " seconds.")

    attestation.close()
    trustedlog.close()
