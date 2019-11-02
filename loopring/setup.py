import os
import subprocess
import config
import time
from zipfile import ZipFile, ZIP_DEFLATED

def mpc_setup(circuit):
    circuit_filename = config.get_circuit_filename(circuit)
    params = config.get_params_filename(circuit)
    if not os.path.exists(params):
        os.makedirs(os.path.dirname(params), exist_ok=True)
    subprocess.check_call([config.phase2_repo_path + "phase2/target/release/new", circuit_filename, params])
    return params

if __name__ == "__main__":
    start = time.time()
    with ZipFile(config.get_zip_filename(0), 'w', ZIP_DEFLATED) as zip_file:
        circuits = config.get_circuits()
        for idx, circuit in enumerate(circuits):
            print("Circuit " + str(idx+1) + "/" + str(len(circuits)) + ":")

            block = config.generate_block(circuit)
            circuit_filename = config.export_circuit(circuit)
            params = mpc_setup(circuit)

            # Add the params file to the zip file
            zip_file.write(params, os.path.basename(params))

            # delete the files
            os.remove(params)
            os.remove(circuit_filename)
            os.remove(block)

    # calculate the hash of the file
    hash = config.hash_file(config.get_zip_filename(0))
    print("SHA256 hash of the contribution is: " + str(hash))

    end = time.time()
    print("Setup took " + str(end - start) + " seconds.")
