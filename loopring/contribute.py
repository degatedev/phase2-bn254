import os
import sys
import subprocess
import config
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

if __name__ == "__main__":
    contribute_beacon = False
    if len(sys.argv) == 2:
        contribute_beacon = (sys.argv[1] == "beacon")

    circuits = config.get_circuits()
    print("Contributing to " + str(len(circuits)) + " circuits.")
    if contribute_beacon:
        entropy = ""
    else:
        entropy = input("Type some random text and press [ENTER] to provide additional entropy...\n")

    index = config.find_latest_contribution_index()

    start_contribution = config.get_zip_filename(index)
    new_contribution = config.get_zip_filename(index+1)

    attestation = open("attestation.txt", "w")
    attestation.write("[Feel free to share anything you'd like here]\n\n\n\n\n\n\n")
    attestation.write("!!!Don't modify anything from this point on!!!\n")
    attestation.write("----------------------------------------------\n")

    if contribute_beacon:
        print_and_log(attestation, "Contributing the beacon!")

    # calculate the hash of the contribution we start from
    start_hash = config.hash_file(start_contribution)
    print_and_log(attestation, "\nStarting from contribution " + str(index) + " with sha256 hash " + str(start_hash) + " (please check if this is correct)\n")

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
    except:
        print_and_log(attestation, "\nAn error occured while contributing! Please try again!\n")
        os.remove(new_contribution)
        pass

    # calculate the hash of the contribution we start from
    end_hash = config.hash_file(new_contribution)

    print_and_log(attestation, "\nDone! Thank you for contributing as participant " + str(index+1) + "!")
    print_and_log(attestation, "Your contribution has sha256 hash " + str(end_hash))
    print_and_log(attestation, "Please upload '" + new_contribution + "'.")
    print_and_log(attestation, "Also please fill out 'attestation.txt' and sign it by running 'python3 sign_attestation.py' and send us 'signed_attestation.txt'.")

    attestation.close()