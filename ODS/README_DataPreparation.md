# Data Preparation
## Data Introduction
The dataset contains 1 million+ trips collected by 1,3000+ taxi cabs during 5 days (2015.1.3-2015.1.7) and are stored as `.h5` files. Each h5 file contains `n` trips of the day. For each trip, it has three fields `lon` (longitude), `lat` (latitude), `tms` (timestamp). 
- trips_150103.h5
- trips_150104.h5
- trips_150105.h5
- trips_150106.h5
- trips_150107.h5
## Requirements
- Windows 10/11
- WSL2 (Ubuntu 20.04)
- Docker Desktop (Windows, integrated with WSL2)
- Julia >= 1.0 (installed in WSL2)
## Package Installation
The required packages for julia can be installed by executing the following command:
```bash
julia -e 'using Pkg; Pkg.add("HDF5"); Pkg.add("CSV"); Pkg.add("DataFrames"); Pkg.add("Distances"); Pkg.add("StatsBase"); Pkg.add("JSON"); Pkg.add("Lazy"); Pkg.add("JLD2"); Pkg.add("ArgParse"); Pkg.add("FileIO")'
```
## Dataset Preparation
### Traffic Dataset
```bash
git clone https://github.com/hongfangao/Data_Platform.git
cd Data_Platform
mkdir -p data/h5path data/jldpath
```
Download the [dataset](https://pan.quark.cn/s/b30e6b7cd379) and put the extracted *.h5 files into `Data_Platform/data/h5path.`


### Map of Harbin

#### Method - Pull from existing image 

1. Pull Docker and Run Container

	#### x86/amd64 Users
	```bash
	git clone git@github.com:hujilin1229/barefoot.git
	cd barefoot
	docker pull garygb/barefoot_map
	docker run -it -p 5432:5432 --name="harbin-map" -v ${PWD}/map/:/mnt/map garygb/barefoot_map:latest
	```


2. To detach the interactive shell from a running container without stopping it, use the escape sequence Ctrl-p + Ctrl-q.

    If we want to attach it again, we can do

    ```bash
    docker attach <container id>
    ```

3. Make sure the container is running ("up").

    ``` bash
    docker ps -a
    ...
    ```


4. We can restart the created container (if it is stopped)
	
	```bash
	docker start --interactive harbin_map
	root@acef54deeedb# service postgresql start
	```

### Map Matching & Run Julia Code

**Ensure the Docker map server is running in the background.**


**Steps**:
1. In WSL2, go to the project directory:
   ```bash
   cd ~/Data_Platform/julia
   ```
2. Run map matching:
   ```bash
   julia -p 8 mapmatch.jl --inputpath ../data/h5path --outputpath ../data/jldpath
   ```
   where `8` is the number of cpu cores available in our machine. The map matching results are stored in `Data_Platform/data/jldpath`.

Once the map matching process is finished, we will get 5 `jld2` files.
(`trips_150103.jld2` to `trips_150107.jld2`).

The 5 `.jld2` files contains the following information:
input roads and points、mapping results of input points、additional points during mapmatching and additional information (road fractions, geo location, direction)

- trips_150103.jld2
- trips_150104.jld2
- trips_150105.jld2
- trips_150106.jld2
- trips_150107.jld2

## References:
[Learning Travel Time Distributions with Deep Generative Model](http://www.ntu.edu.sg/home/lixiucheng/pdfs/www19-deepgtt.pdf) (**WWW-19**)

[Barefoot for China Cities](https://github.com/boathit/barefoot)

[Open Street Map](https://www.openstreetmap.org)

P. Newson and J. Krumm. Hidden Markov Map Matching Through Noise and Sparseness. In Proceedings of International Conference on Advances in Geographic Information Systems, 2009.
