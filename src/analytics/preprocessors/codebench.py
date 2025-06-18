
import os
import pandas as pd
from analytics.ps2_dataset import LinkTablePreprocessor, Preprocessor
import yaml
from spec.enums import MainTableColumns as Cols


class YAMLLinkURLPreprocessor(LinkTablePreprocessor):

    def __init__(self, flatten: bool = False):
        self.flatten = flatten
        self.has_shown_warning = False
        self.root_path = None

    def apply(self, dataset, link_table_name, link_table):
        self.root_path = dataset.data_config.root_path
        if "URL" not in link_table.columns:
            return link_table
        objects = link_table["URL"].apply(self.url_to_object)
        if self.flatten:
            flattened_objects = objects.apply(self.flatten_object).tolist()
            new_cols = pd.DataFrame(flattened_objects)
            link_table = pd.concat([link_table, new_cols], axis=1)
        else:
            link_table["Data"] = link_table["URL"].apply(self.url_to_object)
        return link_table

    def url_to_object(self, url: str):
        # Fixes a bug in an early draft
        if url.startswith("./output"):
            url = url.replace("./output", "")
        url = os.path.join(self.root_path, url)
        try:
            with open(url, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            if not self.has_shown_warning:
                print(f"Error reading YAML file at {url}: {e}. Hiding future warnings.")
                self.has_shown_warning = True
            return None

    @staticmethod
    def flatten_object(obj: dict) -> dict:
        """
        Flattens a nested dictionary into a single-level dictionary.
        Key names are a concatenation of the parent keys and the current key,
        separated by underscores.
        """
        def flatten(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        return flatten(obj)

class CodeBenchExamPerformance:
    """
    Preprocessor that adds exam performance data to the link table.
    Currently a bit buggy because not every student takes every exam...
    """

    def apply(self, dataset):
        if not dataset.link_table_preprocessors.any(lambda p: isinstance(p, YAMLLinkURLPreprocessor)):
            raise ValueError("YAMLLinkURLPreprocessor must be included to use CodeBenchExamPerformance.")
        assignments = dataset.get_link_table("Assignment")
        scores = dataset.get_link_table("AssignmentSubject")
        total_weights = assignments.groupby("class-number").weight.sum()
        assignments = assignments.merge(total_weights.rename("total_weight"), on="class-number")
        assignments["weight_norm"] = assignments["weight"] / assignments["total_weight"]
        scores = scores.merge(assignments, on=Cols.AssignmentID, how='left')
        scores[Cols.Score] = scores["grade"] / 10 # Seems to always be out of 10
        scores["weighted_score"] = scores[Cols.Score] * scores["weight_norm"]
        scores = scores[scores["type"] == "exam"]
        exam_scores = scores.groupby(["class-number", Cols.SubjectID]).weighted_score.sum().rename("exam_total").reset_index()
        return exam_scores



