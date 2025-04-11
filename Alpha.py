import os
import sys
import subprocess
import platform
import tempfile
import re
import requests
from urllib.parse import urljoin


def run_command(command, description=""):
    print(f"\n[INFO] {description}...")
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"[SUCCESS] {description} completed!\n")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} failed: {e}\n")
        sys.exit(1)


def get_script_directory():
    return os.path.dirname(os.path.abspath(__file__))


def get_cpu_cores():
    while True:
        try:
            cores = int(input("Enter the number of CPU cores for compilation: ").strip())
            if cores > 0:
                return cores
        except ValueError:
            pass
        print("Invalid input. Try again.")


def get_linux_distro():
    try:
        result = subprocess.run(["lsb_release", "-ds"], capture_output=True, text=True, check=True)
        return result.stdout.strip().strip('"')
    except:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        return line.strip().split("=")[1].strip('"')
        except:
            return "Unknown"


def detect_os():
    os_info = platform.system()
    kernel_version = platform.release()
    distro_info = get_linux_distro() if os_info == "Linux" else "N/A"

    if os.name == "nt":
        os_type = "Windows"
    elif "microsoft" in kernel_version.lower():
        os_type = "WSL"
    else:
        os_type = "Linux"

    print("\n[INFO] Detected Operating System:")
    print(f"    OS Type: {os_type}")
    print(f"    Kernel Version: {kernel_version}")
    print(f"    Distro Info: {distro_info}\n")

    return os_type, distro_info


def get_latest_geant4_version():
    base_url = "https://gitlab.cern.ch/geant4/geant4/-/archive/"
    response = requests.get("https://gitlab.cern.ch/geant4/geant4/-/tags")
    matches = re.findall(r'v(\d+\.\d+(?:\.\d+)?)', response.text)
    versions = sorted(set(matches), key=lambda x: list(map(int, x.split("."))), reverse=True)
    if not versions:
        print("[ERROR] Could not detect Geant4 versions.")
        sys.exit(1)

    print("Available Geant4 versions:")
    for i, ver in enumerate(versions[:5]):
        print(f"  [{i+1}] v{ver}")

    while True:
        try:
            choice = int(input("Choose a version to install (1-5): "))
            if 1 <= choice <= 5:
                return versions[choice - 1]
        except ValueError:
            pass
        print("Invalid input. Try again.")


def install_packages(distro):
    if "arch" in distro.lower():
        pkg_cmd = "sudo pacman -Sy --noconfirm cmake gcc binutils glew libjpeg-turbo libpng libtiff giflib libxml2 openssl fftw qt5-base qt5-tools mesa glu libxmu"
    elif any(name in distro.lower() for name in ["ubuntu", "debian", "mint"]):
        pkg_cmd = "sudo apt update && sudo apt install -y cmake cmake-curses-gui g++ gcc binutils libx11-dev libxpm-dev libxft-dev libxext-dev libglew-dev libjpeg-dev libpng-dev libtiff-dev libgif-dev libxml2-dev libssl-dev libfftw3-dev qtbase5-dev qtchooser qttools5-dev-tools libgl1-mesa-dev libglu1-mesa-dev libxmu-dev"
    elif "opensuse" in distro.lower():
        pkg_cmd = "sudo zypper install -y cmake gcc gcc-c++ libX11-devel libXpm-devel libXft-devel libXext-devel glew-devel libjpeg-devel libpng-devel libtiff-devel giflib-devel libxml2-devel libopenssl-devel fftw3-devel libqt5-qtbase-devel Mesa-libGL-devel Mesa-libGLU-devel libXmu-devel"
    elif "rocky" in distro.lower() or "rhel" in distro.lower():
        pkg_cmd = "sudo dnf install -y cmake gcc gcc-c++ binutils libX11-devel libXpm-devel libXft-devel libXext-devel glew-devel libjpeg-turbo-devel libpng-devel libtiff-devel giflib-devel libxml2-devel openssl-devel fftw-devel qt5-qtbase-devel qt5-qttools-devel mesa-libGL-devel mesa-libGLU-devel libXmu-devel"
    elif "fedora" in distro.lower():
        if platform.release().startswith("41"):
            pkg_cmd = "sudo dnf5 install -y cmake gcc gcc-c++ binutils qt5-qtbase-devel qt5-qttools-devel mesa-libGL-devel mesa-libGLU-devel libXmu-devel"
        else:
            pkg_cmd = "sudo dnf install -y cmake gcc gcc-c++ binutils qt5-qtbase-devel qt5-qttools-devel mesa-libGL-devel mesa-libGLU-devel libXmu-devel"
    else:
        print("[WARNING] Distro not recognized. Please install dependencies manually.")
        return

    run_command(pkg_cmd, "Installing dependencies")


def install_geant4():
    os_type, distro = detect_os()
    if os_type == "Windows":
        print("\n[WARNING] Script only supports Linux or WSL. Windows script is under development.\n")
        sys.exit(1)

    script_dir = get_script_directory()
    geant4_dir = os.path.join(script_dir, "Geant4")
    os.makedirs(geant4_dir, exist_ok=True)
    os.chdir(geant4_dir)

    version = get_latest_geant4_version()
    tarball = f"geant4-v{version}.tar.gz"
    tar_url = f"https://gitlab.cern.ch/geant4/geant4/-/archive/v{version}/{tarball}"
    src_dir = f"geant4-v{version}"
    build_dir = f"geant4-v{version}-build"

    if os.path.exists(tarball):
        print(f"[WARNING] {tarball} already exists.")
        choice = input("Do you want to [R]edownload, [S]kip, or [A]bort? (R/S/A): ").strip().lower()
        if choice == 'r':
            run_command(f"rm -f {tarball}", "Removing existing tarball")
            run_command(f"wget {tar_url}", "Downloading Geant4 Source")
        elif choice == 's':
            print("[INFO] Using existing tarball.")
        else:
            print("[INFO] Aborting.")
            sys.exit(0)
    else:
        run_command(f"wget {tar_url}", "Downloading Geant4 Source")

    run_command(f"tar xzfv {tarball}", "Extracting Source Code")

    if os.path.exists(build_dir):
        if os.listdir(build_dir):
            print(f"[WARNING] Build dir '{build_dir}' not empty.")
            choice = input("[C]lear, [S]kip, or [A]bort? (C/S/A): ").strip().lower()
            if choice == 'c':
                run_command(f"rm -rf {build_dir}", "Clearing build directory")
                os.makedirs(build_dir)
            elif choice == 's':
                print("[INFO] Continuing with existing build dir.")
            else:
                print("[INFO] Aborting.")
                sys.exit(0)
    else:
        os.makedirs(build_dir)

    os.chdir(build_dir)

    install_packages(distro)

    install_path = os.path.join(script_dir, "Geant4", f"geant4-v{version}-install")
    print(f"[INFO] Install path: {install_path}\n")

    instructions = f"""
[INSTRUCTIONS]
1. After CMake opens, you'll see: EMPTY CACHE
   - Press 'c' to configure
   - Press 'e' to exit the warning

2. Now edit the following settings (use arrow keys to navigate):
   - First, go to `CMAKE_INSTALL_PREFIX`, press Enter,
     then paste the following path using Shift+Ctrl+V:
       {install_path}
     Press Enter again. If it updates from /usr/local, it's set.

Turn ON (ideal settings):
   - GEANT4_INSTALL_DATA
   - GEANT4_USE_OPENGL_X11
   - GEANT4_USE_QT
   - GEANT4_USE_RAYTRACER_X11
   (You can enable more features if desired.)

4. Press 'c' again to configure. Repeat until 'g' is available.
5. Press 'g' to generate the Makefile.
6. After closing CMake, return to the terminal.
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        f.write(instructions)
        temp_path = f.name

    run_command(f"xdg-open {temp_path}", "Opening CMake Instructions")
    input("Press Enter to open the CMake configuration...")
    run_command(f"ccmake ../{src_dir}", "Running CMake")

    input("Press Enter after completing configuration in CMake...")

    cores = get_cpu_cores()
    run_command(f"make -j{cores}", "Compiling Geant4")
    run_command("make install", "Installing Geant4")

    alias_cmd = f'alias geant4make="source {install_path}/share/Geant4/geant4make/geant4make.sh"'
    bashrc = os.path.join(os.path.expanduser("~"), ".bashrc")
    with open(bashrc, "a") as f:
        f.write(f"\n{alias_cmd}\n")

    print("\n[INFO] Added alias to .bashrc. Run 'source ~/.bashrc' to activate it.")
    print("[SUCCESS] Geant4 v{version} installed successfully!")


if __name__ == "__main__":
    install_geant4()