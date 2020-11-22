import os
import subprocess
import config
from zipfile import ZipFile

def mpc_export_keys(circuit):
    # Export the params to bellman vk/pk json files
    params = config.get_params_filename(circuit)
    bellman_vk = config.get_bellman_vk_filename(circuit)
    bellman_pk = config.get_bellman_pk_filename(circuit)
    if not os.path.exists(bellman_vk):
        os.makedirs(os.path.dirname(bellman_vk), exist_ok=True)
    if not os.path.exists(bellman_pk):
        os.makedirs(os.path.dirname(bellman_pk), exist_ok=True)
    subprocess.check_call([config.phase2_repo_path + "phase2/target/release/export_keys", params, bellman_vk, bellman_pk])

    # Use the vk/pk json files to creates the vk/pk files compatible with ethsnarks
    # vk
    vk = config.get_vk_filename(circuit)
    if not os.path.exists(vk):
        os.makedirs(os.path.dirname(vk), exist_ok=True)
    subprocess.check_call(["python3", config.phase2_repo_path + "phase2/tools/vk2ethsnarks.py", bellman_vk, vk])
    # pk
    pk = config.get_pk_filename(circuit)
    block = config.generate_block(circuit)
    subprocess.check_call([config.circuit_executable, "-createpk", bellman_pk, pk])

    # remove files
    os.remove(bellman_vk)
    os.remove(bellman_pk)
    os.remove(block)

if __name__ == "__main__":
    index = config.find_latest_contribution_index()
    print("Exporting keys using contribution " + str(index))

    # calculate the hash of the file
    hash = config.hash_file(config.get_zip_filename(index))
    print("SHA256 hash of contribution: " + str(hash))

    with ZipFile(config.get_zip_filename(index), 'r') as zip_file:
        circuits = config.get_circuits()
        for idx, circuit in enumerate(circuits):
            print("Circuit " + str(idx+1) + "/" + str(len(circuits)) + ":")

            params = config.get_params_filename(circuit)
            # extract the params file from the downloaded file
            zip_file.extract(os.path.basename(params), os.path.dirname(params))
            # export keys
            mpc_export_keys(circuit)
            # delete the file
            os.remove(params)
