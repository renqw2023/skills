---
name: deepresearch-conversation
description: Deep ReSearch Conversation is provided by Baidu for multi-round streaming conversations with "Deep Research" agents. "In-depth research" is a long-process task involving multi-step reasoning and execution, which is different from the ordinary "question-and-answer". A dialogue that requires the user to repeatedly verify and correct it until a satisfactory answer is reached.
metadata: { "openclaw": { "emoji": "📌", "requires": { "bins": ["python", "curl"], "env":["BAIDU_API_KEY"]},"primaryEnv":"BAIDU_API_KEY" } }
---

# AI PPT Generation

This skill allows OpenClaw agents to make in-depth discussions with users on a certain topic or subject and be able to interact deeply with them


## API table
|    name    |               path              |            description                |
|------------|---------------------------------|---------------------------------------|
|DeepresearchConversation|/v2/agent/deepresearch/run|Deep Research conversation is provided by Baidu for multi-round streaming conversations with "Deep Research" agents.|
|ConversationCreate|/v2/agent/deepresearch/create|Used to create a new Agent dialogue session, a conversation_id will be returned upon successful invocation|
|FileUpload|/v2/agent/file/upload|file upload |
|FileParseSumbit|/v2/agent/file/parse/submit|submit a task for parsing uploaded file|
|FileParseQuery|/v2/agent/file/parse/query|query a task result of file parsing task|


## Workflow

1. If a user is discussing a topic for the first time without providing any files, they only need to call the Deep ReSearch Conversation interface (DeepresearchConversation) at the beginning, and it will automatically generate a new conversation.
2. If a user wants to discuss a certain topic based on some given files, they need to call the conversation creation interface (ConversationCreate) to create a conversation before starting the Deep ReSearch Conversation interface(DeepresearchConversation), and then upload the files with file upload interface (FileUpload).
3. If the file upload is successful, please remember to call the file parsing task submission interface (FileParseSumbit) again to create a file parsing task.
4. After the file parsing task is successfully created, it is necessary to call the file parsing query interface （FileParseQuery） every few seconds to check whether the file parsing is successful or has failed
5. If the file parsing is successful, then you can start calling the Deep ReSearch Conversation interface (DeepresearchConversation) and discussing a certain topic based on these files. The entire discussion process is a deep interactive mode. During the process, you need to constantly ask the user whether the direction of their thinking is accurate until the user is satisfied. If the file upload fails, it will prompt that the given file may not be installed for the discussion topic.
6. If the previous round of dialogue is interrupted and terminated, the next round of dialogue needs to obtain the interrupt ID and session ID of the previous round as the input to continue the conversation
7. The DeepresearchConversation API executes the Python script located at `scripts/deepresearch_conversation.py`
8. The DeepresearchConversation API is an sse streaming return interface. If a structured outline was generated in the previous round of dialogue, the user needs to modify and confirm the outline. If no modification is required, the outline data generated in the previous round only needs to be used as the input for the next round of dialogue
9. If The DeepresearchConversation API interface is not called for the first time, you need to bring along the structured outline of the in-depth research report generated in the previous session; otherwise, an error interruption will be prompted. If you need to continue the conversation, you should bring along both the interrupt_id returned from the previous session and the structured outline.
10. The DeepresearchConversation API needs to be repeatedly called and deeply understood during the interaction with users

## APIS

### ConversationCreate API 

#### Parameters

no parameters

#### execute shell 
```bash
curl -X POST "https://qianfan.baidubce.com/v2/agent/deepresearch/create" \
-H "Host: qianfan.baidubce.com" \
-H "X-Appbuilder-From: openclaw" \
-H "Authorization: $BAIDU_API_KEY" \
-H "Content-Type: application/json" \
-d '{}'
```

### FileUpload API 

#### Parameters

- `agent_code`: Take the fixed default value of "deepresearch"（required）
- `conversation_id`: from ConversationCreate API return（required）
- `file`: Binary file content (choose one from file_url), and the number of files uploaded should be no more than 10. limit condition:
  * Text files (.doc,.docx,.txt,.pdf,.ppt,.pptx) 
    + txt: A single file ≤ 10MB 
    + pdf: A single file ≤ 100MB and ≤ 3000 pages (any excess pages will be automatically ignored) 
    + ppt/.pptx: ≤ 400 pages (any excess pages will be automatically ignored) 
    + doc/.docx: A single file ≤ 100MB and ≤ 2500 pages (any excess pages will be automatically ignored) 
  * Table files (.xlsx,.xls) 
    + Single file ≤ 100MB 
    + no more than 150,000 characters per line (calculated by the number of characters) 
    + Only one Sheet is supported Supported encodings: UTF-8, GBK, GB2312, GB18030, ASCII 
  * Image classes (.png,.jpg,.jpeg,.bmp) 
    + Each image should be no more than 10 MB 
  * Audio category (.wav,.pcm) 
    + Single file ≤ 10MB
- `file_url`: file URL (choose one from File) The URL must be accessible on the public network. The file format restrictions are the same as those described in the file.


#### if local file upload,execute shell 
```bash
curl -X POST "https://qianfan.baidubce.com/v2/agent/file/upload" \
  -H "Authorization: Bearer $BAIDU_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -H "X-Appbuilder-From: openclaw" \
  -F "agent_code=deepresearch" \
  -F "conversation_id=$conversation_id" \
  -F "file=@local_file_path"
```

#### if file Url ,execute shell 
```bash
curl -X POST "https://qianfan.baidubce.com/v2/agent/file/upload" \
  -H "Authorization: Bearer $BAIDU_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -H "X-Appbuilder-From: openclaw" \
  -F "agent_code=deepresearch" \
  -F "conversation_id=$conversation_id" \
  -F "file_url=$file_url"
```

### FileParseSumbit API 

#### Parameters

- `file_id`: from FileUpload API return（required）

#### execute shell 
```bash
curl -X POST --location 'https://qianfan.baidubce.com/v2/agent/file/parse/submit' \
--header 'Authorization: Bearer $BAIDU_API_KEY' \
--header 'Content-Type: application/json' \
--header 'X-Appbuilder-From: openclaw' \
--data '{
    "file_id": "$file_id"
}'
```

### FileParseQuery API 

#### Parameters

- `task_id`: from FileParseSumbit API return（required）

#### execute shell 
```bash
curl -X GET --location 'https://qianfan.baidubce.com/v2/agent/file/parse/query?task_id=$task_id' \
--header 'Authorization: Bearer $BAIDU_API_KEY' --header 'X-Appbuilder-From: openclaw'
```

### DeepresearchConversation API 

#### Parameters

- `query`: The question entered by the user. Determine whether it is a simple question and answer or in-depth research based on the query input by the user.（required）
- `file_ids`: the file id list from FileUpload API and parse success, If this round of dialogue requires passing in files, you need to first obtain the conversation_id through the ConversationCreate API, and then obtain the file ID list through the FileUpload API. The file parsing status can be obtained through the FileParseSumbit API and the FileParseQuery API.
- `interrupt_id`: In response to the Agent's" "Demand clarification" "Or" "Outline confirmation" It must be filled in when requested. The content of this field was obtained within the content.text.data field in the previous round of DeepresearchConversation API SSE response.
- `conversation_id`: First-round dialogue: Optional. It will be automatically generated by the server and returned in the response. Alternatively, the conversation id can be obtained in advance through the ConversationCreate API. Subsequent conversation: Must be filled in to maintain context continuity. conversation_id can be obtained in the sse data stream
- `structured_outline`: A structured outline of a deep research report. If the output of the previous round of dialogue is outline confirmation data, users can make modifications based on the outline content. For the next round of dialogue requests, just bring the final outline. The Agent will strictly generate subsequent research reports based on this data. the strucure as below:
```json
{
    "title": "string",
    "locale": "string",
    "description": "string",
    "sub_chapters": [
        {
            "title": "string",
            "locale": "string",
            "description": "string",
            "sub_chapters": [{}]
        }
    ]
}
```
- `version`: Report generation version, specifying the policy preference when generating the report. The default is Standard: Lite: Performance first, end-to-end report generation is controlled within 10 minutes, and faster response speed is achieved by reducing search depth. Standard: Quality first, ensuring the depth, accuracy and completeness of the report. The generation time is relatively long.

#### Example shell
```bash
python3 scripts/deepresearch_conversation.py '{"query": "the question to talk","file_ids":["file_id_1","file_id_2"],"interrupt_id":"interrupt_id","conversation_id":"conversation_id","structured_outline":{"title": "string","locale": "string","description": "string","sub_chapters": [{"title": "string","locale": "string","description": "string","sub_chapters": [{}]}},"version": "Standard"}'
```
