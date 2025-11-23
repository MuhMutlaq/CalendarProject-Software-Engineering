# Two-Stage Event Extraction Architecture

## Overview

The system now uses a **two-stage approach** for extracting and filtering exam events:

1. **Stage 1: Extraction** - AI extracts ALL events from the document
2. **Stage 2: Filtering** - Backend filters events based on client criteria

This architecture provides better accuracy, flexibility, and separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FILE UPLOAD                               │
│              (PDF or Image with exam schedule)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  STAGE 1: EXTRACTION                         │
│              (model.py - Gemini AI)                          │
│                                                              │
│  Task: Extract ALL events from the document                 │
│  Input: Document content (text or image)                    │
│  Output: Complete list of all exams with:                   │
│    - Date                                                    │
│    - Time                                                    │
│    - Major-Level                                             │
│    - Offered To                                              │
│    - Course Code                                             │
│    - Course Name                                             │
│                                                              │
│  No filtering at this stage - extract everything!           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ ALL EVENTS (unfiltered)
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  STAGE 2: FILTERING                          │
│              (app.py - Python logic)                         │
│                                                              │
│  Task: Filter events based on client criteria               │
│  Input:                                                      │
│    - All extracted events                                    │
│    - Client filters (major_level, offered_to)               │
│                                                              │
│  Filtering Rules:                                            │
│    1. If no filters → return all events                     │
│    2. If major_level only → filter by level                 │
│    3. If offered_to only → filter by major                  │
│    4. If both → filter by both conditions                   │
│                                                              │
│  Special Rules:                                              │
│    - "Offered To: All" matches any major filter             │
│    - Multi-major entries (e.g., "CS, SE") are checked       │
│                                                              │
│  Output: Filtered list of relevant events                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ FILTERED EVENTS
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                RETURN TO CLIENT                              │
│        (Frontend displays filtered results)                  │
└─────────────────────────────────────────────────────────────┘
```

## Benefits of Two-Stage Approach

### 1. **Better Accuracy**
- AI focuses solely on extraction without complex filtering logic
- Simpler prompt = more reliable extraction
- AI doesn't need to interpret matching rules

### 2. **Flexibility**
- Can change filtering rules without re-prompting AI
- Can add new filter types easily
- Can implement fuzzy matching or advanced logic

### 3. **Debugging**
- Can see ALL extracted events before filtering
- Easy to diagnose if issue is in extraction or filtering
- Response.json shows complete extraction

### 4. **Performance**
- Extract once, filter multiple times if needed
- Can cache extracted events
- Faster iterations on filter logic

### 5. **Separation of Concerns**
- AI does what it's good at: vision and extraction
- Python does what it's good at: logic and filtering
- Clear responsibility boundaries

## Code Structure

### Stage 1: Extraction (model.py)

```python
class PromptChat:
    def get_content(self, page: str, is_image: bool = False,
                    image_path: str = None) -> str:
        """
        Extract ALL events from document.
        No filtering - just pure extraction.
        """
        # Simplified prompt focused on extraction
        prompt = """Extract ALL exams with these columns:
        - Date
        - Time
        - Major-Level
        - Offered To
        - Course Code
        - Course Name

        Return as JSON array."""

        # Send to Gemini API
        # Returns complete list of all events
```

**Key Points:**
- No `major_level` or `offered_to` parameters
- Prompt is simple and focused
- Always extracts everything
- Returns raw JSON array

### Stage 2: Filtering (app.py)

```python
def filter_events_by_criteria(events: List[Dict], major_level: Optional[str],
                               offered_to: Optional[str]) -> List[Dict]:
    """
    Filter extracted events based on client criteria.
    """
    if not major_level and not offered_to:
        return events  # No filters

    filtered = []
    for event in events:
        level_match = True
        major_match = True

        # Check major level
        if major_level:
            level_match = (event['major_level'] == major_level)

        # Check offered to
        if offered_to:
            if event['offered_to'] == 'All':
                major_match = True
            elif offered_to in event['offered_to']:
                major_match = True
            else:
                major_match = False

        # Include if both match
        if level_match and major_match:
            filtered.append(event)

    return filtered
```

**Key Points:**
- Pure Python logic
- Easy to modify and test
- Handles edge cases (All, multi-major)
- Fast execution

### Integration (app.py)

```python
def extract_events_from_file(file_path, filename, major_level=None,
                             offered_to=None):
    """Two-stage extraction and filtering."""

    # STAGE 1: Extract ALL events
    logger.info("Stage 1: Extracting all events")
    all_events = extract_events_with_ai(text, is_image, image_path)
    logger.info(f"Extracted {len(all_events)} total events")

    # STAGE 2: Filter events
    logger.info("Stage 2: Filtering events")
    filtered_events = filter_events_by_criteria(
        all_events, major_level, offered_to
    )
    logger.info(f"Returning {len(filtered_events)} filtered events")

    return filtered_events
```

## Filtering Logic Examples

### Example 1: No Filters
```python
Input: major_level=None, offered_to=None
Result: All events returned (no filtering)
```

### Example 2: Major Level Only
```python
Input: major_level="2", offered_to=None
Extracted Events:
  - Event A: Level 2, CS
  - Event B: Level 2, SE
  - Event C: Level 3, CS

Result: Events A, B (both Level 2)
```

### Example 3: Offered To Only
```python
Input: major_level=None, offered_to="CS"
Extracted Events:
  - Event A: Level 2, CS
  - Event B: Level 2, SE
  - Event C: Level 1, All

Result: Events A, C (CS and All)
```

### Example 4: Both Filters
```python
Input: major_level="2", offered_to="CS"
Extracted Events:
  - Event A: Level 2, CS      ✓ Match
  - Event B: Level 2, SE      ✗ Wrong major
  - Event C: Level 2, All     ✓ Match (All = any major)
  - Event D: Level 3, CS      ✗ Wrong level

Result: Events A, C
```

### Example 5: Multi-Major Entry
```python
Input: major_level="2", offered_to="CS"
Extracted Events:
  - Event A: Level 2, "CS, SE"  ✓ Match (CS in list)
  - Event B: Level 2, "AI, CIS" ✗ No match

Result: Event A
```

## Logging and Debugging

The two-stage approach provides excellent visibility:

### Backend Logs
```
INFO: Stage 1: Extracting all events from file
INFO: Processing image file: exam_schedule.jpg
INFO: Sending request to Gemini model for event extraction.
INFO: Response received successfully from Gemini model.
INFO: Extracted 25 total events from file

INFO: Stage 2: Filtering events based on client criteria
INFO: Filtered 25 events down to 8 events
INFO: Returning 8 events after filtering
```

### Check Raw Extraction
```bash
# View ALL events extracted by AI (before filtering)
cat backend/Response.json
```

This shows exactly what the AI extracted, helping diagnose issues.

## Testing

### Test Extraction (Stage 1)
```python
# Extract without filters
events = extract_events_from_file(file_path, filename, None, None)
# Should return ALL events
```

### Test Filtering (Stage 2)
```python
# Create test data
test_events = [
    {"major_level": "2", "offered_to": "CS", "course_code": "CS201"},
    {"major_level": "2", "offered_to": "All", "course_code": "MATH101"},
    {"major_level": "3", "offered_to": "CS", "course_code": "CS301"},
]

# Test filter
filtered = filter_events_by_criteria(test_events, "2", "CS")
# Should return 2 events (CS201 and MATH101)
```

## Error Handling

### Stage 1 Errors
- API key missing
- Invalid file format
- No text extracted from PDF
- Gemini API error
- Invalid JSON response

### Stage 2 Errors
- Invalid filter values
- Empty event list (not an error, just empty result)

## Performance Considerations

### Extraction (Slow)
- Gemini API call (network latency)
- Vision processing for images
- Text processing for PDFs

### Filtering (Fast)
- Pure Python logic
- Milliseconds for 100+ events
- No external API calls

### Optimization
- Cache extracted events if user changes filters
- Process large files in background
- Implement pagination for 100+ events

## Future Enhancements

### Possible Additions
1. **Fuzzy Matching**: Match "Computer Science" to "CS"
2. **Multi-Level Filtering**: Filter by multiple levels (e.g., "2, 3")
3. **Date Range Filtering**: Filter by date range
4. **Time Slot Filtering**: Filter by time preferences
5. **Conflict Detection**: Check for schedule conflicts
6. **Smart Suggestions**: Suggest filters based on extracted data

### Caching Strategy
```python
# Cache extraction results
cache_key = hash(file_content)
if cache_key in extraction_cache:
    all_events = extraction_cache[cache_key]
else:
    all_events = extract_events_with_ai(...)
    extraction_cache[cache_key] = all_events

# Fast re-filtering
filtered_events = filter_events_by_criteria(all_events, new_filters)
```

## Summary

The two-stage architecture provides:
- ✅ **Clarity**: Each stage has a single responsibility
- ✅ **Reliability**: Simpler AI prompt = better extraction
- ✅ **Flexibility**: Easy to modify filtering logic
- ✅ **Debuggability**: Can inspect results at each stage
- ✅ **Performance**: Fast filtering, cacheable extraction
- ✅ **Maintainability**: Clean separation of concerns

This is a **better design** than having the AI do both extraction and filtering in one step.
