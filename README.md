# tagz

This is a script to automatically tag repos on GitHub.


## Installation

Install using pip:

    pip install -r requirements.txt


## Sample usage

* To create a tag:

        python tagz.py -r mozilla/fireplace -c create -t 2014.02.11

NOTE: annotated tags are used by default (-a). If you want lightweight tags,
      you can pass -l:

    $ python tagz.py -l -r mozilla/fireplace -c create -t 2014.02.11

ALSO: this script will use whatever type of tag the first found refname is.
      You cannot use this script to mix use of the two in the same repo.

* To create multiple tags:

        python tagz.py -r mozilla/monolith,mozilla/solitude,mozilla/webpay,mozilla/commbadge,mozilla/fireplace,mozilla/marketplace-stats,mozilla/monolith-aggregator,mozilla/rocketfuel,mozilla/zamboni -c create -t 2014.02.11

* To delete a tag:

        python tagz.py -r mozilla/fireplace -c delete -t 2014.02.11

* To cherry-pick a commit onto a tag:

        python tagz.py -r mozilla/fireplace -c cherrypick -t 2014.02.11 -s b4dc0ffee

* To remove a commit from a tag:

        python tagz.py -r mozilla/fireplace -c revert -t 2014.02.11 -s b4dc0ffee


## Authors

[See list of authors.](https://github.com/cvan/tagz/blob/master/AUTHORS.md)
