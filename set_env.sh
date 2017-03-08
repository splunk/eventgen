alias orca="docker run --rm -it --name orca -e USER=$USER -v $HOME/.orca:/root/.orca -v $HOME/.ssh:/root/.ssh -v $(pwd -P):/orca-home repo.splunk.com/splunk/products/orca"
