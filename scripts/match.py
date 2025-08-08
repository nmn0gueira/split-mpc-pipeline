import argparse
import subprocess
import sys
import os
import tempfile
import logging
import pandas as pd
import numpy as np


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

TEMP_FILES = ["alszote.pp", "PrivateID.pp"] # These are always generated with pid anyway

protocol_requirements = {
    "psi": "ids_only",
    "pid": "ids_only",
    "cpsi": "ids_only_receiver",
    "ps3i": "full",
    "ps3i-xor": "full"
}


def cleanup_temp_files(temp_files):
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except OSError as e:
            logging.debug(f"Error deleting temporary file {temp_file}: {e}")


def extract_ids_to_temp(input_path):
    id_only_df = pd.read_csv(input_path, header=None, usecols=[0])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='') as tmp_file:
        id_only_df.to_csv(tmp_file.name, index=False, header=False)
        TEMP_FILES.append(tmp_file.name)
        logging.info(f"Extracted IDs to temporary file: {tmp_file.name}")
        return tmp_file.name
    

def get_effective_input_path(protocol_name, input_path, input_id_path, **kwargs):
    protocol_input_type = protocol_requirements.get(protocol_name)
    
    if protocol_input_type == "ids_only":
        if input_id_path:
            return input_id_path
        else:
            return extract_ids_to_temp(input_path)
        
    elif protocol_input_type == "ids_only_receiver":
        if kwargs.get('is_server'):
            if input_id_path:
                return input_id_path
            else:
                return extract_ids_to_temp(input_path)
        else:
            if input_id_path:
                logging.warning(f"Input ID path provided but protocol '{protocol_name}' does not require it. Ignoring {input_id_path}.")
            return input_path

    elif protocol_input_type == "full":
        return input_path
    
    else:
        logging.error(f"Unknown protocol input type for '{protocol_name}'")
        return None


def post_process_psi(input_path, output_path):
    input_df = pd.read_csv(input_path, header=None)
    output_df = pd.read_csv(output_path, header=None)
    output_df = pd.merge(output_df, input_df, on=0, how='left').drop(columns=[0])
    output_df.to_csv(output_path, index=False, header=False)


def post_process_cpsi(input_path, output_path, is_server):
    output_df = pd.read_csv(output_path, header=None)

    # MP-SPDZ cannot handle hex strings directly so we convert them to integers
    for col in output_df.columns[1:]:
        #output_df[col] = output_df[col].map(lambda x: int(x, 16))  # Full share
        #output_df[col] = output_df[col].map(lambda x: int(x[16:], 16)) # Second half of the share only
        output_df[col] = output_df[col].map(lambda x: int(x[24:], 16)) # Last fourth of the share only

    if is_server:
        output_dir = os.path.dirname(output_path)
        mapping_path = os.path.join(output_dir, 'mapping.out')
        TEMP_FILES.append(mapping_path)

        with open(mapping_path, 'r') as f:
            mapping = np.array(f.read().strip().split('\n'), dtype=int)

        input_df = pd.read_csv(input_path, header=None)
        server_columns = pd.DataFrame(
            0, 
            index=output_df.index, 
            columns=input_df.columns[1:], 
            dtype=object)
        
        server_df_start = len(output_df.columns)
        output_df = pd.concat([output_df, server_columns], axis=1, ignore_index=True)

        output_df.iloc[mapping, server_df_start:] = input_df.iloc[:, 1:].values

    output_df.to_csv(output_path, index=False, header=False)


def post_process_ps3i_xor(output_path):
    comapny_feature_path = output_path + '_company_feature.csv'
    partner_feature_path = output_path + '_partner_feature.csv'
    TEMP_FILES.append(comapny_feature_path)
    TEMP_FILES.append(partner_feature_path)
    output_df_company = pd.read_csv(comapny_feature_path, header=None)
    output_df_partner = pd.read_csv(partner_feature_path, header=None)
    output_df = pd.concat([output_df_company, output_df_partner], axis=1)
    output_df.to_csv(output_path, index=False, header=False)


def post_process_pid(input_path, output_path):
    input_df = pd.read_csv(input_path, header=None)
    output_df = pd.read_csv(output_path, header=None)

    mapping_series = pd.Series(output_df.index, index=output_df[0])
    mapped_indices = mapping_series.loc[output_df.iloc[:len(input_df), 1]].to_numpy()

    true_output_df = pd.DataFrame(
        0, 
        index=output_df.index, 
        columns=input_df.columns, 
        dtype=object)

    true_output_df.iloc[mapped_indices, 0] = 1
    true_output_df.iloc[mapped_indices, 1:] = input_df.iloc[:, 1:].to_numpy()

    true_output_df.to_csv(output_path, index=False, header=False)


def post_process(protocol_name, input_path, output_path, **kwargs):
    if protocol_name == 'psi':
        post_process_psi(input_path, output_path)
    elif protocol_name == 'cpsi':
        post_process_cpsi(input_path, output_path, kwargs.get('is_server'))
    elif protocol_name == 'ps3i':
        pass
    elif protocol_name == 'ps3i-xor':
        post_process_ps3i_xor(output_path)
    elif protocol_name == 'pid':
        post_process_pid(input_path, output_path)
    else:
        logging.error(f"No transformation logic defined for '{protocol_name}'")
        sys.exit(1)

def get_modification_time(file_path):
    try:
        return os.stat(file_path).st_mtime
    except FileNotFoundError:
        return None

def run_protocol(protocol_name, input_path, input_id_path, output_path, address, protocol_args):
    is_server = address.split(':')[0] == '0.0.0.0'
    check_path = output_path  # The way check_path is used is very scuffed but it works for now
    if protocol_name == 'ps3i-xor':
        check_path += '_company_feature.csv'
    modification_time = get_modification_time(check_path)

    effective_input_path = get_effective_input_path(protocol_name, input_path, input_id_path, is_server=is_server)

    protocol_commands = {
        "psi": lambda: ['./match/volepsi/out/build/linux/frontend/frontend', '-in', effective_input_path, '-out', output_path, '-ip', address, '-r', str(1) if is_server else str(0)] + protocol_args,
        "cpsi": lambda: ['./match/volepsi/out/build/linux/frontend/frontend', '-cpsi', '-in', effective_input_path, '-out', output_path, '-ip', address, '-r', str(1) if is_server else str(0)] + protocol_args,
        "ps3i": lambda: ['./match/Private-ID/target/release/cross-psi-server' if is_server else './match/Private-ID/target/release/cross-psi-client', '--input', effective_input_path, '--output', output_path, '--host' if is_server else '--company', address] + protocol_args,
        "ps3i-xor": lambda: ['./match/Private-ID/target/release/cross-psi-xor-server' if is_server else './match/Private-ID/target/release/cross-psi-xor-client', '--input', effective_input_path, '--output', output_path, '--host' if is_server else '--company', address] + protocol_args,
        "pid": lambda: ['./match/Kunlun/build/main_pid', '--in', effective_input_path, '--out', output_path, '--address', address] + protocol_args
    }

    if protocol_name not in protocol_commands:
        logging.error(f"Unknown protocol: {protocol_name}")
        sys.exit(1)

    cmd = protocol_commands[protocol_name]()

    try:
        logging.info(f"Running {protocol_name} protocol with command: {' '.join(cmd)}")
        subprocess.run(cmd, text=True, stdout=sys.stdout, stderr=sys.stderr, check=True)
        if modification_time == get_modification_time(check_path):
            raise subprocess.CalledProcessError(1, cmd, "Output file not modified. Protocol may have failed or produced no output.")
        post_process(protocol_name, input_path, output_path, is_server=is_server)
    except subprocess.CalledProcessError as e:
        logging.error(f"Protocol failed with exit code {e.returncode}")
        sys.exit(e.returncode)


def main():
    parser = argparse.ArgumentParser(description="Protocol wrapper script")
    parser.add_argument("--input", type=str, required=True, help="Input file for the protocol")
    parser.add_argument("--input-id", type=str, help="Optional CSV with IDs only (used if needed)")
    parser.add_argument("--output", type=str, required=True, help="Output path for the protocol output")
    parser.add_argument("--address", type=str, required=True, help="Address to use (for server: 0.0.0.0:port, for client: ip:port)")
    parser.add_argument("protocol", help="The protocol to run (psi, cpsi, ps3i, ps3i-xor, pid)")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Additional protocol specific arguments")

    args = parser.parse_args()

    try:
        run_protocol(args.protocol, args.input, args.input_id, args.output, args.address, args.args)
    finally:
        cleanup_temp_files(TEMP_FILES)

if __name__ == "__main__":
    main()
