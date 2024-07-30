# Combat_Core
Source code for [AXI Combat](https://github.com/AX-I/AXI_Combat).

Two render backends are implemented: an OpenGL pipeline, and a custom OpenCL software rasterizer (deprecated).

There are also basic AI, networking, physics, animation, and audio capabilities.

## Building from source

### Windows, Mac OSX
Download Python >= 3.8
```
python -m pip install -r requirements.txt
```

### Ubuntu Linux
After clean installation:
```
sudo apt update
sudo apt install python3-pip tk8.6-dev python3-tk python3-pil.imagetk
sudo apt install libasound-dev portaudio19-dev
pip3 install xlib
pip3 install -r requirements.txt
```

Drivers might be troublesome
```
sudo add-apt-repository ppa:intel-opencl/intel-opencl
sudo apt update
sudo apt install intel-opencl-icd

sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt install nvidia-opencl-icd-384
```
