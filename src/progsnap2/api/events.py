from typing import List, Optional, Union
from pydantic import BaseModel, create_model
from enum import Enum

from spec import datatypes
from spec.spec_definition import Column, EnumType, EventType, ProgSnap2Spec, Requirement
from spec.enums import EventType


class MainTableEventBase(BaseModel):
    """
    A class representing an event in the main table.
    """


# TODO: Explore if we can add documentation to fields or enum values
# TODO: Should probably have two ways of defining an event:
# 1) Define all the columns in the event
# 2) Define the non-event-specific columns in the event, and then add an AnyAdditionalColumns
#    This could generate an instance of (1) easily
# Could also just create one class that has all columns *and* the additional columns,
# which I like for the simplicity but dislike for the redundancy...
# Either way, I still like the idea of using TS codegen for helper methods, but this
# means they'll break if someone updates the server spec which I dont like...
class DataModelGenerator:
    """
    A class that generates the data model for the events.
    """

    MainTableEvent: type
    main_event_additional_columns: List[type] = []
    AnyAdditionalColumns: type

    def __init__(self, ps2_spec: ProgSnap2Spec):
        self.ps2_spec = ps2_spec
        self.event_type_enum = self.create_event_type_enum_type()
        self.enum_type_map = {et.name: et for et in ps2_spec.enum_types}
        self.__enum_map = {}
        self.MainTableEvent = self.generate_main_table_event()
        self.main_event_additional_columns = self.generate_main_event_additional_columns()
        self.AnyAdditionalColumns = Union[tuple(self.main_event_additional_columns)]

    def create_event_type_enum_type(self) -> Enum:
        """
        Generate the event type enum type.
        """
        # return Enum("EventType", {
        #     v.name: v.name
        #     for v in self.ps2_spec.MainTable.event_types
        # })
        return EventType

    def get_enum_for_type(self, enum_definition: EnumType):
        """
        Create an enum from a list of enum values.
        """

        stored = self.__enum_map.get(enum_definition.name)

        if stored is None:
            stored = Enum(enum_definition.name, {
                v.name: v.name
                for v in enum_definition.values
            })
            self.__enum_map[enum_definition.name] = stored

        return stored

    def get_type_for_column(self, col: Column):
        if col.name == "EventType":
            return self.event_type_enum
        elif col.datatype == datatypes.PS2Datatype.Enum:
            return self.get_enum_for_type(self.enum_type_map[col.name])
        else:
            return col.datatype.python_type

    def get_field_representation(self, type, required: bool):
        """
        Get the field representation for a column.
        """
        if required:
            return (type, ...)
        else:
            return (Optional[type], None)

    def generate_main_table_event(self) -> type[MainTableEventBase]:
        fields = {}
        for col in self.ps2_spec.main_table.columns:
            type = self.get_type_for_column(col)
            required = col.requirement == Requirement.Required
            fields[col.name] = self.get_field_representation(type, required)

        return create_model("MainTableEvent", __base__=MainTableEventBase, **fields)

    def generate_event_specific_columns_class(self, event_type: EventType) -> type:
        """
        Generate a class for the event-specific columns.
        """
        fields = {}
        for col in self.ps2_spec.main_table.columns:
            if not event_type.is_column_specific_to_event(col.name):
                continue
            type = self.get_type_for_column(col)
            required = event_type.is_column_required(col.name)
            fields[col.name] = self.get_field_representation(type, required)

        name = "Columns" + event_type.name
        name = name.replace(".", "")
        return create_model(name, **fields)

    def generate_main_event_additional_columns(self) -> List[type[MainTableEventBase]]:
        """
        Generate classes to hold required and optional event-specific columns for
        each event.
        """
        column_classes = []
        for event_type in self.ps2_spec.main_table.event_types:
            subclass = self.generate_event_specific_columns_class(event_type)
            column_classes.append(subclass)
        return column_classes
