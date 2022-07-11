# RunPodPy
Version 0.2.0

RunPodPy is an unofficial python API wrapper and CLI for https://runpod.io/

## Usage
`$ python3 -m runpodpy`  
usage: __main__.py [-h] [--debug] [--config_file CONFIG_FILE] [--runpod_api.URL RUNPOD_API.URL] [--runpod_api.API_KEY RUNPOD_API.API_KEY]
                   {stop,destroy,terminate,start,run,resume,create,list} ...

RunPodPy

commands:
  {stop,destroy,terminate,start,run,resume,create,list}
    stop                Stop a pod
    destroy (terminate)
                        Destroy a pod
    start (run, resume)
                        Start a pod
    create              Create a pod
    list                List pods

options:
  -h, --help            show this help message and exit
  --debug               Enable debug logging
  --config_file CONFIG_FILE
                        Path to config file
  --runpod_api.URL RUNPOD_API.URL, --URL RUNPOD_API.URL
                        Base URL of runpod api
  --runpod_api.API_KEY RUNPOD_API.API_KEY, --API_KEY RUNPOD_API.API_KEY
                        Your RunPod.io api key