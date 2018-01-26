import sys
from collections import defaultdict, OrderedDict

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from guidedmodules.models import AppSource
from guidedmodules.module_sources import MultiplexedAppSourceConnection, AppSourceConnectionError
class Command(BaseCommand):
    help = 'Prints a list of all apps in the configured app stores.'

    def handle(self, *args, **options):
        # Initialize a data structure into which we'll collect stats.
        stats = {
            "apps": defaultdict(lambda : {
                "modules": {
                    "count": 0
                },
                "questions": {
                    "count": 0
                },
            }),
            "sources": defaultdict(lambda : {
                "apps": {
                    "count": 0
                }
            }),
            "vendors": defaultdict(lambda : {
                "apps": {
                    "count": 0
                }
            }),
        }

        # Loop over all AppSources and apps within those sources and collect
        # stats as we iterate.
        self.iterate_apps(stats)

        # Post-process the stats to form summary stats.
        self.post_process(stats)

        # Show the stats.
        import rtyaml
        rtyaml.dump(stats, sys.stdout)

    def iterate_apps(self, stats):
        # Iterate over all apps.
        for source in AppSource.objects.all():
            try:
                with source.open() as conn:
                    for app in conn.list_apps():
                        self.collect_app_stats(app, stats)
            except AppSourceConnectionError as e:
                print(e)

    def collect_app_stats(self, app, stats):
        app_name = app.store.source.slug + "/" + app.name

        # Count up information by app....

        # Count up information found in the modules.
        for module_id, module_data in app.get_modules():
            stats["apps"][app_name]["modules"]["count"] += 1
            stats["apps"][app_name]["questions"]["count"] += len(module_data.get("questions", []))

        # Count up information by source.
        stats["sources"][app.store.source.slug]["apps"]["count"] += 1

        # Count up information by venor listed in the app metadata.
        metadata = app.get_catalog_info()
        vendor = metadata.get("vendor")
        if vendor not in stats["vendors"]:
            stats["vendors"][vendor]["apps"]["count"] += 1

    def post_process(self, stats):
        stats["apps"] = summary_stats_recursive(stats["apps"].items())
        stats["sources"] = summary_stats_recursive(stats["sources"].items())
        stats["vendors"] = summary_stats_recursive(stats["vendors"].items())

def summary_stats(sequence, key, labels=None):
    # Compute numerical summary stats, i.e. min, 1st quartile, mean,
    # median, 3rd quartile, max, for the sequence. `key` is a function
    # that takes an item in sequence as an argument and returns a
    # number over which the stats are generated. The quartiles are
    # through a simplified perecntile formula that assumes no averaging
    # across bins is needed.

    from math import log

    ret = OrderedDict([ ("n", 0), ("min",  None), ("1st.qt",  None), ("mean",  None), ("median",  None), ("3rd.qt",  None), ("max",  None) ])
    
    if len(sequence) == 0:
        # If there are no items, there are no stats.
        return ret
    
    # Sort the items by the key function.
    sorted_seq = sorted(list(sequence), key=key)

    # Return the stats.
    n = len(sorted_seq)
    ret["n"] = n
    ret["min"] = key(sorted_seq[0])
    ret["1st.qt"] = key(sorted_seq[n//4])
    ret["mean"] = sum(key(item) for item in sequence) / n
    ret["median"] = key(sorted_seq[n//2])
    ret["3rd.qt"] = key(sorted_seq[3*n//4])
    ret["max"] = key(sorted_seq[-1])

    # Round the mean to a certain number of significant figures
    # based on the number of items in the set.
    sigfigs = int(log(n)/log(10) + 1)
    ret["mean"] = round(ret["mean"], -int(log(ret["mean"])/log(10)) +sigfigs)

    # Add examples
    if labels:
        ret["min_ex"] = labels(sorted_seq[0])
        ret["1st.qt_ex"] = labels(sorted_seq[n//4])
        ret["median_ex"] = labels(sorted_seq[n//2])
        ret["3rd.qt_ex"] = labels(sorted_seq[3*n//4])
        ret["max_ex"] = labels(sorted_seq[-1])

    return ret

def summary_stats_recursive(sequence, key=lambda x : x, labeler = lambda x : None):
    # Assume all items in sequence have the same dict structure where
    # all leaves are numbers. Yield summary statistics for all leaves in
    # a dict of a similar structure.

    # If there are no items, there is no structure.
    if len(sequence) == 0:
        return { }

    # Use the key function to extract the item we are copying structure
    # from, based on the first item in sequence.
    model = key(list(sequence)[0])

    # Base case.
    if isinstance(model, (int, float)):
        return summary_stats(sequence, key, labels=labeler)

    # Main case.
    elif isinstance(model, dict):
        return OrderedDict([
            (name, summary_stats_recursive(sequence, key = lambda x : key(x)[name], labeler = labeler) )
            for name in model
        ])

    # If there's a tuple, assume this is a key-value pair and we're computing
    # statistics over the value, but we'll report the key as a label for an example.
    elif isinstance(model, tuple):
        return summary_stats_recursive(sequence, key = lambda x : key(x)[1], labeler = lambda x : key(x)[0])

    else:
        raise TypeError(repr(model) + " should be a number or dict.")
