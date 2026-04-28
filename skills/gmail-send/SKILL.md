---
name: gmail-send
display_name: "Gmail Send"
description: "Send an email via Gmail API"
category: communication
icon: mail
skill_type: sandbox
catalog_type: platform
requirements: "httpx>=0.25,google-auth>=2.0,requests>=2.20"
resource_requirements:
  - env_var: GMAIL_CREDENTIALS_JSON
    name: "Gmail Service Account JSON"
    description: "Google service account credentials JSON"
  - env_var: GMAIL_USER_EMAIL
    name: "Gmail User Email"
    description: "Email address to send from (delegated)"
tool_schema:
  name: gmail_send
  description: "Send an email via Gmail"
  parameters:
    type: object
    properties:
      to:
        type: "string"
        description: "Recipient email"
      subject:
        type: "string"
        description: "Email subject"
      body:
        type: "string"
        description: "Email body (plain text)"
    required: [to, subject, body]
---
# Gmail Send
Send an email via Gmail API
