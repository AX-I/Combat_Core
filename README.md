# Combat_Core
Source code for [AXI Combat](https://github.com/AX-I/AXI_Combat).

Two render backends are implemented: a custom OpenCL software rasterizer, and a standard OpenGL pipeline.

There are also basic AI, networking, physics, animation, and audio capabilities.

## Building from source

### Windows
Download Python >= 3.6
```
python -m pip install numpy numexpr moderngl pillow pyautogui pyaudio requests pywin32
```
Download PyOpenCL from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyopencl
```
python -m pip install pyopencl-win_amd64.whl
```

### Mac OSX
Download Python >= 3.6
```
python -m pip install pyopencl numpy numexpr moderngl pillow pyautogui pyaudio requests tkmacosx
```

### Ubuntu Linux
After installing Ubuntu 18.04.1 LTS:
```
sudo apt update
sudo apt install python3-pip tk8.6-dev python3-tk python3-pil.imagetk
pip3 install numpy numexpr
pip3 install pyopencl xlib moderngl
sudo apt install libasound-dev portaudio19-dev
pip3 install pyaudio
```
Drivers might be troublesome
```
sudo add-apt-repository ppa:intel-opencl/intel-opencl
sudo apt update
sudo apt install intel-opencl-icd

sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt install nvidia-opencl-icd-384
```
