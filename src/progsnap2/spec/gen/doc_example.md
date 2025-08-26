
# Metadata Table

## Version
* *Datatype*: String
* *Default value*: 1.0

This property specifies the current version of the ProgSnap 2 standard that these files adhere to. This allows the standard to change over time. ProgSnap2 versions use semantic versioning and should therefore be string values.

## CodeStateRepresentation
* *Datatype*: Enum
* *Default value*: None

**Enum Values**:

| Name      | Description                                                                                                                   |
| --------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Table     | CodeStates will be stored in a CodeStates table along with other tables in the database.                                      |
| Directory | CodeStates will be stored in individual folders, with each folder containing all code files, organized by SubjectID.          |
| Git       | CodeStates will be stored in Git repositories, with commit hashes used as CodeStateIDs, organized by SubjectID and ProjectID. |

This property specifies which CodeState representation is used by the dataset.  This property must be specified using one of the legal values listed below.

# Main Events Table

## Required Universal Columns

### EventType
* *Requirement Type*: Required
* *Datatype*: Enum

**Enum Values**:

| Name          | Description                        | Required Columns                | Optional Columns |
| ------------- | ---------------------------------- | ------------------------------- | ---------------- |
| Session.Start | Marks the start of a work session. | SessionID                       |                  |
| Session.End   | Marks the end of a work session.   | SessionID                       |                  |
| Compile       | ...                                | CodeStateSection, CompileResult | EventInitiator   |

Every line logged in a dataset must be associated with a specific event, where events can be categorized as one of several possible types. Users are encouraged to apply the built-in enum values whenever possible, but if a new event type is necessary, the coder may define a new enum type beginning with the string "X-". The metadata of the associated dataset should define what the new EventTypes mean.

### SubjectID
...

## Optional Universal Columns

## Event-specific Columns

### ParentEventID
* *Requirement Type*: Event-specific
* *Datatype*: ID
* *Required for these [EventTypes](#eventtype)*:
  * Compile.Error
  * Compile.Warning

Certain events are hierarchical, where multiple child events might be associated with a single parent event. In these cases, the parent event should be referenced in this column by its EventID value.

# LinkTables

## LinkSubject
A link table with additional information about each student.

*Required ID Columns*:
* [SubjectID](#subjectid)

*Additional Columns*:

### MidtermExamScore
* *Requirement type*: Optional
* *Datatype*: Real

The student's score between 0-1 on the midterm exam.
