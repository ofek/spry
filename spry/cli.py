import argparse
from .api import get


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('-t', '--threads', type=int, default=4)
    c_args = vars(parser.parse_args())

    get(c_args['url'], c_args['output'], c_args['threads'], start=True)
