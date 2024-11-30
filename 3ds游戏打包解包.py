import os
import subprocess
import tkinter as tk
from tkinter import filedialog

def modify_header(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    header_start = data.find(b'\x4E\x43\x53\x44')
    if header_start!= -1:
        new_data = data[:header_start - 256] + b'\xFF' * 256 + data[header_start:]

        with open(file_path, 'wb') as f:
            f.write(new_data)

def extract_partition(file_path, rom_folder, partition_number):
    partition_folder = os.path.join(rom_folder, f'cfa{partition_number}')
    os.makedirs(partition_folder, exist_ok=True)

    partition_command = f'3dstool -xvt{partition_number}f cci "{partition_folder}\\{partition_number}.cfa" "{file_path}"'
    partition_process = subprocess.run(partition_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(partition_process.stdout)

    cfa_command = f'3dstool -xvtf cfa "{partition_folder}\\{partition_number}.cfa" --header "{partition_folder}\\ncchheader.bin" --romfs "{partition_folder}\\romfs.bin"'
    cfa_process = subprocess.run(cfa_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(cfa_process.stdout)

    romfs_bin_path = os.path.join(partition_folder, 'romfs.bin')
    romfs_folder = os.path.join(partition_folder, 'romfs')
    romfs_command = f'3dstool -xvtf romfs "{romfs_bin_path}" --romfs-dir "{romfs_folder}"'
    romfs_process = subprocess.run(romfs_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(romfs_process.stdout)

def extract_exefs(exefs_bin_path, exh_bin_path, exefs_folder, exefs_header_path):
    with open(exh_bin_path, 'rb') as exh_file:
        exh_data = exh_file.read(0x10)
        use_u = exh_data[0x0D] == 1

    exefs_command = f'3dstool -{"xvtfu" if use_u else "xvtf"} exefs "{exefs_bin_path}" --exefs-dir "{exefs_folder}" --header "{exefs_header_path}"'
    exefs_process = subprocess.run(exefs_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(exefs_process.stdout)

def extract_3ds():
    file_path = filedialog.askopenfilename(filetypes=[("3DS files", "*.3ds")])
    if not file_path:
        return

    modify_header(file_path)

    dir_path = os.path.dirname(file_path)
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    rom_folder = os.path.join(dir_path, file_name)
    os.makedirs(rom_folder, exist_ok=True)

    cci_command = f'3dstool -xvt0f cci "{rom_folder}\\0.cxi" "{file_path}" --header "{rom_folder}\\ncsdheader.bin"'
    cci_process = subprocess.run(cci_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(cci_process.stdout)

    if 'INFO: partition 1' in cci_process.stdout:
        extract_partition(file_path, rom_folder, '1')
    if 'INFO: partition 7' in cci_process.stdout:
        extract_partition(file_path, rom_folder, '7')

    cxi0_folder = os.path.join(rom_folder, 'cxi0')
    os.makedirs(cxi0_folder, exist_ok=True)

    cxi_command = f'3dstool -xvtf cxi "{rom_folder}\\0.cxi" --header "{cxi0_folder}\\ncchheader.bin" --exh "{cxi0_folder}\\exh.bin" --plain "{cxi0_folder}\\plain.bin" --exefs "{cxi0_folder}\\exefs.bin" --romfs "{cxi0_folder}\\romfs.bin"'
    cxi_process = subprocess.run(cxi_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(cci_process.stdout)

    romfs_bin_path = os.path.join(cxi0_folder, 'romfs.bin')
    exefs_bin_path = os.path.join(cxi0_folder, 'exefs.bin')
    exh_bin_path = os.path.join(cxi0_folder, 'exh.bin')
    romfs_folder = os.path.join(cxi0_folder, 'romfs')
    exefs_folder = os.path.join(cxi0_folder, 'exefs')
    exefs_header_path = os.path.join(exefs_folder, 'exefsheader.bin')

    romfs_command = f'3dstool -xvtf romfs "{romfs_bin_path}" --romfs-dir "{romfs_folder}"'
    romfs_process = subprocess.run(romfs_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(romfs_process.stdout)

    extract_exefs(exefs_bin_path, exh_bin_path, exefs_folder, exefs_header_path)

    print(f"Extraction complete for {file_name}")

def run_command(command):
    process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(process.stdout)
    return process

def pack_exefs_romfs(folder_path):
    # 处理cxi0中的exefs和romfs
    cxi0_exefs_path = os.path.join(folder_path, "cxi0", "exefs")
    cxi0_romfs_path = os.path.join(folder_path, "cxi0", "romfs")
    exefs_command = f"3dstool -cvtfz exefs {folder_path}/cxi0/exefs.bin --header {folder_path}/cxi0/exefs/exefsheader.bin --exefs-dir {folder_path}/cxi0/exefs"
    run_command(exefs_command)
    romfs_command = f"3dstool -cvtf romfs {folder_path}/cxi0/romfs.bin --romfs-dir {folder_path}/cxi0/romfs"
    run_command(romfs_command)

    # 处理cfa1 - cfa7中的exefs和romfs
    for i in range(1, 8):
        cfa_path = os.path.join(folder_path, f"cfa{i}")
        if not os.path.exists(cfa_path):
            continue
        cfa_romfs_path = os.path.join(cfa_path, "romfs")
        romfs_command = f"3dstool -cvtf romfs {cfa_path}/romfs.bin --romfs-dir {cfa_romfs_path}"
        run_command(romfs_command)

def pack_cxi_cfa(folder_path):
    # 处理cxi0打包成cxi
    cxi0_path = os.path.join(folder_path, "cxi0")
    cxi_command = f"3dstool -cvtf cxi {folder_path}/0.cxi --header {cxi0_path}/ncchheader.bin --exh {cxi0_path}/exh.bin --plain {cxi0_path}/plain.bin --exefs {cxi0_path}/exefs.bin --romfs {cxi0_path}/romfs.bin --key0"
    run_command(cxi_command)

    # 处理cfa1 - cfa7打包成cfa
    for i in range(1, 8):
        cfa_path = os.path.join(folder_path, f"cfa{i}")
        if not os.path.exists(cfa_path):
            continue
        cfa_command = f"3dstool -cvtf cfa {folder_path}/{i}.cfa --header {cfa_path}/ncchheader.bin --romfs {cfa_path}/romfs.bin"
        run_command(cfa_command)

def pack_cci(folder_path):
    dir_path = os.path.dirname(folder_path)
    file_name = os.path.basename(folder_path)
    partitions = []
    for i in range(1, 8):
        cfa_path = os.path.join(folder_path, f"cfa{i}")
        if os.path.exists(cfa_path):
            partitions.append(i)

    partition_str = ''.join(str(i) for i in partitions)
    cci_command = f"3dstool -cvt0{partition_str}f cci {folder_path}/0.cxi"
    for i in partitions:
        cci_command += f" {folder_path}/{i}.cfa"
    cci_command += f" {dir_path}/{file_name}.3ds --header {folder_path}/ncsdheader.bin"
    run_command(cci_command)
    print("打包3ds rom成功")

def on_extract_button_click():
    extract_3ds()

def on_pack_button_click():
    folder_path = filedialog.askdirectory()
    if folder_path:
        pack_exefs_romfs(folder_path)
        pack_cxi_cfa(folder_path)
        pack_cci(folder_path)

root = tk.Tk()
root.title("3DS游戏解包与打包")
root.geometry("600x300")
root.resizable(True, True)

extract_button = tk.Button(root, text="解包3ds游戏", command=on_extract_button_click)
extract_button.pack(pady=20)

pack_button = tk.Button(root, text="打包3ds游戏", command=on_pack_button_click)
pack_button.pack(pady=20)

root.mainloop()