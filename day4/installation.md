#instruction to create an environment to run .ipynb file
$ conda create --name diec python=3.7
$ conda activate diec

#inside diec environment
$ pip install scikit-learn==0.22.0
$ pip install protobuf==3.20.3
$ pip install protobuf==3.20.3
$ pip install ipykernel
$ pip install pandas
$ pip install matplotlib
$ pip install seaborn
$ pip install unzip
$ python -m ipykernel install --user --name diec --display-name "diec"