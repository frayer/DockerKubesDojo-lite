# ~~ Introduction to Kubernetes ~~

So far we've build a Container Image and executed it locally in Docker.  While this works great for local development, we eventually want to run our Container in a cluster of machines.  There could be potentially hundreds of machines in this cluster.  If we wanted to run 3 replicas or instances of our applications in the cluster, it would be very tedious, and not at all automated, to log into a few machines in that cluster and run a `docker run <image>` command on each.

This is where Kubernetes comes in.  Instead of me thinking or caring about any particular machine in a Kubernetes cluster, instead I will describe to the cluster what Container I want it to run, and in which configuration.  If I want 3 instances of my Container to run, I'll ask Kubernetes to do that in the form of an API call and let it figure out how to do so.  I don't care how it does it, or on which machine my Container ultimately runs.  I just want Kubernetes to do everything it can to keep 3 of them running.

Kubernetes is a declarative Container Orchestration Engine.  I "declare" to it the configuration I want my Containerized application to be in, and it "orchestrates" the cluster to make sure that happens.

Even though ultimately we would want to run our application in a remote production-grade Kubernetes cluster, we still have the opportunity to run a lightweight Kubernetes instance on our local machines.  Docker Desktop makes this easy, and should have been setup if you followed the setup instructions in the [README.md](../README.md) file.  We will be working with our local Kubernetes instance for this lab.

## Kubernetes Manifests

Our next step is to describe to Kubernetes how to run our Container.  We do that in what are called "Kubernetes Manifests".  In this case, it is specifically called a Kubernetes **Deployment** Manifest, and one has been provided already in the [k8s/deployment.yaml](../k8s/deployment.yaml) file.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    run: cloud-native-demo
  name: cloud-native-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      run: cloud-native-demo
  template:
    metadata:
      labels:
        run: cloud-native-demo
    spec:
      containers:
      - image: cloud-native-demo:1
        imagePullPolicy: IfNotPresent
        name: cloud-native-demo
        resources:
          limits:
            cpu: 1
            memory: 128Mi
          requests:
            cpu: 100m
            memory: 128Mi
      restartPolicy: Always
      terminationGracePeriodSeconds: 2
```

Look through this file for anything familiar.  Does the `image: cloud-native-demo:1` line bring back memories?  This is the same Image tag we used back when running the Container with Docker with the `docker run --rm -it cloud-native-demo:1` command.

There is a lot more going on in this file than we specified on the command line to run it with Docker.  It can be overwhelming at first, but be at ease with a couple of my own observations and experience working with these:

1. I haven't met anyone that's tried to memorize all this syntax.  There is great reference material in the [Kubernetes Docs](https://kubernetes.io/docs/home/), and you'll find yourself copying and pasting a lot from existing examples when starting out.
1. Even though outside of the scope of this tutorial, there are tools that help with templating or generating these larger YAML Kubernetes Manifest files when you really only have a few variables in them you are adjusting.  [Helm](https://helm.sh/) and [Kustomize](https://kustomize.io/) are two popular examples.

Regardless, we are going to work with this example so you have this knowledge to fall back on when working with higher level abstractions later on.

## Apply your first Kubernetes Deployment

From the root of the repository you cloned in [Lab 2](02_docker_build.md) with `git clone https://github.com/frayer/DockerKubesDojo-lite.git`, run the following command.  Semantically, this statement says "Apply the manifest described in the file k8s/deployment.yaml to Kubernetes".

```bash
kubectl apply -f k8s/deployment.yaml
```

You should see the following output:

```bash
deployment.apps/cloud-native-demo created
```

To prove something actually happened, let's ask Kubernetes for information on that Deployment using the following command:

```bash
kubectl get deployments
```

And you should see output like the following:

```bash
NAME                READY   UP-TO-DATE   AVAILABLE   AGE
cloud-native-demo   1/1     1            1           4m35s
```

You may see an indication of `0/1` under the `READY` column.  This means Kubernetes hasn't recognized that your Container is up and ready yet.  Keep running the same command until you see the `1/1` indication.  This indicates `1 of 1` Containers is ready.

## Connecting to the running Container

When we executed locally using Docker, we were able to connect to the running instance of the application in a browser by port-forwarding to port `5000` which the Python application was listening on.  You can do the same in Kubernetes, but first we need to find where the Container is running.  Obviously it's running somewhere on your machine at the moment, but remember that eventually you could be working against a very large cluster of machines.  So we're going to stick with the `kubectl` CLI tool which allows us to query the Kubernetes API for information on our Kubernetes configuration.  You'll get the same user experience locally as you would in any multi-node Kubernetes cluster.

The Kubernetes Deployment we deployed earlier is part of what's called a `Controller` in Kubernetes.  It's a more advanced topic, but essentially you've just given Kuberntes a description of how you want your Container to run, and a Controller is always running somewhere in the background to make sure that's the case.  Your actual Container is running in the context of a `Pod` in Kubernetes terms, and that's where we'll look next to find out where we can port-forward to.

> TIP: The terminology and concepts in Kubernetes are vast.  Walking through samples and repetition are what helped me to come to a better understanding of them on my journey.

Run the following to get a listing of all your `Pods`:

```bash
kubectl get pods
```

Your `Pod` name will have a unique name, but the prefix will start with `cloud-native-demo-`.  The output will look something like the following:

```
NAME                                 READY   STATUS    RESTARTS   AGE
cloud-native-demo-6d96dcb96b-5x725   1/1     Running   0          23m
```

In this example the `Pod` name is `cloud-native-demo-6d96dcb96b-5x725`, and this is what we want to port-forward to in order to access the Python web application in a browser.

Type the following into your command prompt, making sure to replace the `Pod` name with the `Pod` name shown on your local machine.  Remember, they'll all be named differently:

```bash
kubectl port-forward cloud-native-demo-6d96dcb96b-5x725 5000:5000
```

The `5000:5000` at the end semantically says `open a port locally on port 5000 and forward that traffic to port 5000 of the Pod`.  The number to the left of the `:` is the port you want to listen to locally while the number to the right is the port the `Pod` is exposing.

## Validate your connection to the Pod

In your browser, navigate to the URL [http://localhost:5000](http://localhost:5000).  You should see a JSON response similar to that when we ran the Container [locally with Docker](02_docker_build.md).

## Setting environment variables for the Container

Our Python application includes some logic to read Environment Variables.  Reading configuration from Environment Variables is a common technique to ensure we can deploy the same codebase to different environments.  As an example, you don't want to hard-code connection details to a database because you'll likely use a different database in test than you do in production (I hope you do anyway).  Instead, you leave configuration placeholders in your application and determine their values at startup.  This is the [Config](https://12factor.net/config) principle in the 12 Factor App.

So far we have seen the `HOSTNAME` Environment Variable show up in the JSON response in the `env.host` response field:

```json
{
  "appName": "cloud-native-demo",
  "env": {
    "host": "cloud-native-demo-78dbcf7fd9-48lmt",
    "user_defined_1": null,
    "user_defined_2": null,
    "user_defined_3": null
  },
  "redis-host": "localhost",
  "version": "1.0.0"
}
```

We would like to set the others which will show up in the output as `env.user_defined_1`, `env.user_defined_2` and `env.user_defined_3`.  These are retrieved from the following Environment Variables respectively:

```
USER_DEFINED_1
USER_DEFINED_2
USER_DEFINED_3
```

Some of this work has been done for you already in the [k8s/deployment_with_env_vars.yaml](../k8s/deployment_with_env_vars.yaml) Kubernetes Deployment manifest.  Open it and note this new addition to Container Specification section:

```yaml
        env:
        - name: USER_DEFINED_1
          value: Custom value 1
        - name: USER_DEFINED_2
          value: Custom value 2
```

Environment Variables are one of many configuration items you can define for a Kubernetes Deployment.  Others include CPU and Memory resources, storage, and security options.  Setting Environment Variables like this is a gentle introduction to how we define what the industry calls, "Infrastructure as Code".

Apply this configuration to Kubernetes using the `kubectl apply` command used earlier, but specifiy the different file name.

```bash
kubectl apply -f k8s/deployment_with_env_vars.yaml
```

Then immediately list the Pods with the following:

```bash
kubectl get pods
```

If you are quick enough, you might be able to see a new Pod spinning up while the old one is shown as `Terminating`.

```bash
NAME                                 READY   STATUS        RESTARTS   AGE
cloud-native-demo-6d96dcb96b-gkzjd   1/1     Running       0          5s
cloud-native-demo-78dbcf7fd9-vchcc   1/1     Terminating   0          40s
```

In addition to practicing Configuration as Code, you're also seeing another pattern play out here known as Stateless Infrastructure.  Kubernetes didn't try to reconfigure the existing running application or Container.  It just threw away the old and created a new one.  In other words, it didn't try to manipulate the configured **state** of the existing Container.  Instead it started with a fresh instance in the configuration requested.

## Putting it all together

You have now seen how to apply a Deployment to Kubernetes, which in turn creates Pods, which is where the Container ultimately runs.  Using the techniques from before, attempt the following tasks:

1. Set up a port-forward connection to the new Pod configured in the previous step and try to access the web application again on http://localhost:5000 .  Do you see the 2 newly configured values for `env.user_defined_1` and `env.user_defined_2` in the JSON output?
1. Configure the last environment variable of `USER_DEFINED_3` by modifying the `k8s/deployment_with_env_vars.yaml` file.  Apply this updated Deployment to Kubernetes.
1. Again, set up a port-forward connection to the new Pod and make sure you see all 3 values in the JSON output which were derived from the Environment Variables you provided.

## Clean up

We can tear down all this infrastructure as easily as we stood it up.  Run the following command to delete what we've previously deployed:

```bash
kubectl delete -f k8s/deployment_with_env_vars.yaml
```

Next, try to list the Pods using what you learned above.  You'll either see no Pods running, or one or more in a `Terminating` state.  Keep running the command to list the Pods until you don't see them anymore.
