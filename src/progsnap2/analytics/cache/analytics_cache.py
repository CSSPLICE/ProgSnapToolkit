from dataclasses import dataclass
from sqlalchemy import Table, Text
from progsnap2.spec.enums import MainTableColumns as Cols

# indexed_id_columns = [
#     Cols.SubjectID,
#     Cols.AssignmentID,
#     Cols.ProblemID,
#     Cols.CodeStateSection,
#     Cols.CourseID,
#     Cols.CourseSectionID,
#     Cols.TermID,
#     Cols.ProjectID,
#     Cols.SessionID,
#     Cols.TeamID
# ]

class AnalyticsTable:
    __table_name__ = "analytics_cache"

    def create_table(self, metadata) -> Table:
        from sqlalchemy import Column, String, Integer, MetaData
        columns = [
            Column("AnalyticID", String, nullable=False),
            Column("AnalyticVersion", Integer, nullable=False),
            Column("Key", String, nullable=False),
            Column("Result", Text, nullable=False),
            Column("DataHash", String, nullable=False),
        ]
        # Additional columns can be added here as needed
        table = Table(self.__table_name__, metadata, *columns)
        return table

@dataclass
class AnalyticsKey:
    parameters: dict[str,str]
    analytic_id: str
    analytic_version: int