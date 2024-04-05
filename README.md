# DoE-Suite - Design of Experiments

The DoE-Suite is a tool for remote experiment management that allows you to easily orchestrate benchmarking experiments on AWS EC2 machines, the ETHZ Euler cluster, or a set of existing remote machines.
Whether you want to train an ML model on a single instance or run a client-server experiment across multiple instances, DoE-Suite has you covered.

With the DoE-Suite, you can automatically orchestrate and execute a set of experiments based on a simple declarative YAML design file.
The design file follows a DSL that enables you to specify experiments with ease.
Each experiment in a suite defines the involved computing resources (e.g., AWS EC2 instances) as well as a list of run configurations.

To express the run configurations, the DoE-Suite follows the naming convention of Design of Experiments ([DoE](https://en.wikipedia.org/wiki/Design_of_experiments)).
A factor is a parameter that changes between different runs, and in each run, a factor takes a particular level, i.e., value. For example, you could have a factor to vary the load and find the saturation point of a system.

In addition to defining the set of experiments to be run, a suite design file also includes a section on how to process the resulting files, such as performance measurements.

With the DoE-Suite, you can set up your experiment environments, run the experiments, and process the results with a single command. This streamlined approach saves you time and effort, allowing you to focus on analyzing the data and drawing insights from your experiments.


Start an experiment suite:
```sh
make run suite=example01-minimal id=new
```

Terminate all remote resources, e.g., terminate all EC2 instances, and local cleanup, e.g., pycache:
```sh
make clean
```



## More Documentation
More documentation can be found [here](https://nicolas-kuechler.github.io/doe-suite/).


## Contributing

We welcome contributions from anyone interested in improving the tool.
If you're interested in contributing, you can start by checking out our GitHub repository and looking for open issues or feature requests.
You can also improve the documentation, suggest new features, or report bugs by creating a new issue.

If you're not sure where to start, feel free to reach out to us and we'll be happy to guide you.
Thank you to all [contributors](AUTHORS.md) for helping make the DoE-Suite a more powerful and user-friendly tool.

## License

Distributed under the Apache License. See `LICENSE` for more information.

If you use the DoE-Suite in your research, please consider citing this project:
```
@misc{Kuchler2022-doesuite,
  author = {Nicolas K\"{u}chler and Miro Haller and Hidde Lycklama},
  title = {{D}o{E}-{S}uite},
  year = {2022},
  howpublished = {\url{https://github.com/nicolas-kuechler/doe-suite/}}
}
```
