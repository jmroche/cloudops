


cat <<EOF | sudo tee /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward                = 1
EOF

sudo sysctl --system

sudo apt-get update && sudo apt-get install -y containerd 

# make configuration directory for containerd

sudo mkdir -p /etc/containerd

#create a default config file

sudo containerd config default | sudo tee /etc/containerd/config.toml 

# restart containerd 

sudo systemctl restart containerd

# kubernetes requires swap to be disabled
# turn off swap

sudo swapoff -a

# disable swap

sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Install dependency packages:

sudo apt-get update && sudo apt-get install -y apt-transport-https curl

# Download and add GPG key:
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add

# Add Kubernetes to repository list:

sudo apt-add-repository "deb http://apt.kubernetes.io/kubernetes-xenial main"

sudo apt-get update -y

# Install Kubernetes packages:
sudo apt-get install -y kubelet=1.20.1-00 kubeadm=1.20.1-00 kubectl=1.20.1-00

# Turn off automatic updates:
sudo apt-mark hold kubelet kubeadm kubectl


#

# Initialize the Kubernetes cluster on the control plane node using kubeadm (Note: This is only performed on the Control Plane Node):
sudo kubeadm init --pod-network-cidr 192.168.0.0/16

# Set kubectl access:
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Test access to cluster:
kubectl version

# Install Calisco network

# On the Control Plane Node, install Calico Networking:
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check status of Calico components:
kubectl get pods -n kube-system


# Get commands to join nodes to master
kubeadm init

# Join the Worker Nodes to the Cluster
# In the Control Plane Node, create the token and copy the kubeadm join command (NOTE:The join command can also be found in the output from kubeadm init command):
kubeadm token create --print-join-command
# In both Worker Nodes, paste the kubeadm join command to join the cluster:
sudo kubeadm join <join command from previous command>
# In the Control Plane Node, view cluster status:
kubectl get nodes



# bash script 

#!/bin/bash


cat <<EOF | sudo tee /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward                = 1
EOF

sudo sysctl --system

sudo apt-get update && sudo apt-get install -y containerd

# make configuration directory for containerd

sudo mkdir -p /etc/containerd

#create a default config file

sudo containerd config default | sudo tee /etc/containerd/config.toml

# restart containerd

sudo systemctl restart containerd

# kubernetes requires swap to be disabled
# turn off swap

sudo swapoff -a

# disable swap

sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Install dependency packages:

sudo apt-get update && sudo apt-get install -y apt-transport-https curl

# Download and add GPG key:
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add

# Add Kubernetes to repository list:

sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main"

sudo apt-get update -y

# Install Kubernetes packages:
sudo apt-get install -y kubelet=1.20.1-00 kubeadm=1.20.1-00 kubectl=1.20.1-00

# Turn off automatic updates:
sudo apt-mark hold kubelet kubeadm kubectl


#

# Initialize the Kubernetes cluster on the control plane node using kubeadm (Note: This is only performed on the Control Plane Node):
sudo kubeadm init --pod-network-cidr 192.168.0.0/16

# Set kubectl access:
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install Calisco network

# On the Control Plane Node, install Calico Networking:
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml