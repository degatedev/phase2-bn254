import os
import sys
import subprocess
import config
from zipfile import ZipFile

def verify_contribution(circuit, previous_params, new_params):
    subprocess.check_call([config.phase2_repo_path + "phase2/target/release/verify_contribution", circuit, previous_params, new_params])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: <index_of_contribution>")
        exit(1)

    index = int(sys.argv[1])
    print("Verifying contribution " + str(index) + "...")

    new_contribution = config.get_zip_filename(index)
    previous_contribution = config.get_zip_filename(index-1)

    # calculate the hash of the contribution we start from
    new_hash = config.hash_file(new_contribution)
    previous_hash = config.hash_file(previous_contribution)
    print("SHA256 hash of contribution:          " + str(new_hash))
    print("SHA256 hash of previous contribution: " + str(previous_hash))

    with ZipFile(new_contribution, 'r') as new_file, ZipFile(previous_contribution, 'r') as previous_file:
        circuits = config.get_circuits()
        for idx, circuit in enumerate(circuits):
            print("Circuit " + str(idx+1) + "/" + str(len(circuits)) + ":")

            previous_params = config.get_old_params_filename(circuit)
            new_params = config.get_params_filename(circuit)

            # extract the contributions
            previous_file.extract(os.path.basename(previous_params), os.path.dirname(previous_params))
            new_file.extract(os.path.basename(new_params), os.path.dirname(new_params))

            # verify
            block = config.generate_block(circuit)
            circuit_filename = config.export_circuit(circuit)
            verify_contribution(circuit_filename, previous_params, new_params)

            # delete files
            os.remove(previous_params)
            os.remove(new_params)
            os.remove(circuit_filename)
            os.remove(block)

    print("Done! Contribution " + str(index) + " is valid!")
