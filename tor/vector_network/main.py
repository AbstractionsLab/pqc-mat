#!/usr/bin/env python3

import subprocess
import sys
import os
import argparse


def _validate_port_range(port):
    if port < 1 or port > 65535:
        print("Error: Port must be between 1 and 65535")
        sys.exit(1)


def get_user_input_cli():
    parser = argparse.ArgumentParser(
        description="Network scanning tool for SSH and TLS protocols",
        epilog="Example: vector network --protocol ssh --target example.com --port 22"
    )
    parser.add_argument(
        "--protocol",
        choices=["ssh", "tls"],
        required=True,
        help="Protocol to scan (ssh or tls)"
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target domain or IP address"
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port number (1-65535)"
    )

    args = parser.parse_args()

    _validate_port_range(args.port)

    if not args.target or args.target.strip() == "":
        print("Error: Target cannot be empty")
        sys.exit(1)

    return args.protocol, args.port, args.target.strip()


def get_user_input_interactive():
    print("Select protocol")
    print("  1. SSH (port 22)")
    print("  2. TLS (port 443)")
    print("  3. Custom ")
    
    choice = input("Choice (1/2/3) ").strip()

    if choice == "1":
        protocol = "ssh"
        port = 22
    elif choice == "2":
        protocol = "tls"
        port = 443
    elif choice == "3":
        print("\nSelect protocol")
        print("  SSH")
        print("  TLS")
        proto_choice = input("Choice (1/2) ").strip()
        
        if proto_choice == "1":
            protocol = "ssh"
        elif proto_choice == "2":
            protocol = "tls"
        else:
            print("Error: Invalid choice")
            sys.exit(1)
        
        port_input = input("Port ").strip()
        
        if not port_input.isdigit():
            print("Error: Port must be a number")
            sys.exit(1)
        
        port = int(port_input)
        _validate_port_range(port)
    else:
        print("Error: Invalid choice")
        sys.exit(1)

    target = input("Target (domain or IP): ").strip()

    if not target:
        print("Error: Target cannot be empty")
        sys.exit(1)

    return protocol, port, target


def scan_ssh(target, port):
    scan_output = f"{target.replace('.', '_')}_ssh_scan.json"
    zgrab_cmd = f"echo '{target}' | zgrab2 ssh --port {port} -o {scan_output}"

    try:
        subprocess.run(zgrab_cmd, shell=True, check=True, capture_output=True, text=True, timeout=300)

        if not os.path.exists(scan_output):
            print(f"Error: Scan file '{scan_output}' was not created")
            sys.exit(1)

        if os.path.getsize(scan_output) == 0:
            print(f"Error: Scan file '{scan_output}' is empty")
            sys.exit(1)

        print(f"  Scan saved: {scan_output}")
        return scan_output
    except subprocess.CalledProcessError as e:
        print(f"Error: ZGrab2 scan failed - {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: zgrab2 command not found")
        sys.exit(1)


def scan_tls(target, port):
    scan_output = f"{target.replace('.', '_')}_tls_scan.json"
    scan_output_path = os.path.abspath(scan_output)

    if os.path.exists(scan_output_path):
        try:
            os.remove(scan_output_path)
        except OSError as e:
            print(f"Error: Cannot remove existing file '{scan_output_path}': {e}")
            sys.exit(1)

    testssl_path = "/home/vector/tools/testssl.sh/testssl.sh"

    if not os.path.exists(testssl_path):
        print(f"Error: testssl.sh not found at '{testssl_path}'")
        sys.exit(1)

    testssl_cmd = f"{testssl_path} --jsonfile {scan_output_path} {target}:{port}"

    try:
        subprocess.run(testssl_cmd, shell=True, timeout=600)

        if not os.path.exists(scan_output_path):
            print("Error: testssl.sh scan failed - no output file created")
            sys.exit(1)

        if os.path.getsize(scan_output_path) == 0:
            print(f"Error: Scan file '{scan_output_path}' is empty")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print("Error: testssl.sh scan timed out after 600 seconds")
        sys.exit(1)

    print(f"  Scan saved: {scan_output_path}")
    return scan_output_path


def _run_cbom_converter(converter_name, scan_output):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    converter_script = os.path.join(script_dir, converter_name)

    if not os.path.exists(converter_script):
        print(f"Error: '{converter_script}' not found")
        sys.exit(1)

    if not os.path.exists(scan_output):
        print(f"Error: Scan output file '{scan_output}' not found")
        sys.exit(1)

    try:
        result = subprocess.run(
            f"python3 {converter_script} {scan_output}",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout, end='')
    except subprocess.CalledProcessError as e:
        print("Error: CBOM generation failed")
        if e.stderr:
            print(f"Details: {e.stderr}")
        sys.exit(1)


def run(protocol: str, port: int, target: str) -> int:
    _validate_port_range(port)
    if not target or target.strip() == "":
        print("Error: Target cannot be empty")
        return 1
    target = target.strip()
    print(f"\nScanning {target}:{port} ({protocol.upper()})")
    if protocol == "ssh":
        scan_output = scan_ssh(target, port)
        print("\nGenerating CBOM")
        _run_cbom_converter("zgrab2_to_cbom.py", scan_output)
    else:
        scan_output = scan_tls(target, port)
        print("\nGenerating CBOM")
        _run_cbom_converter("testssl_to_cbom.py", scan_output)
    print("\nCompleted")
    return 0


def main():
    if len(sys.argv) > 1:
        protocol, port, target = get_user_input_cli()
    else:
        protocol, port, target = get_user_input_interactive()
    sys.exit(run(protocol, port, target))


if __name__ == "__main__":
    main()
