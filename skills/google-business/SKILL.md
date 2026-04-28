---
name: google-business
display_name: "Google Business Profile"
description: "Manage Google Business Profile listings — reviews, posts, insights, and business info"
category: marketing
icon: store
skill_type: sandbox
catalog_type: platform
requirements: "httpx>=0.25,google-auth>=2.0,requests>=2.20"
resource_requirements:
  - env_var: GOOGLE_BUSINESS_CREDENTIALS_JSON
    name: "Google Business Profile Credentials"
    description: "Google OAuth credentials JSON for Business Profile API access"
tool_schema:
  name: google_business
  description: "Manage Google Business Profile listings — reviews, posts, insights, and business info"
  parameters:
    type: object
    properties:
      action:
        type: "string"
        description: "Which operation to perform"
        enum: ['list_accounts', 'list_locations', 'get_location', 'list_reviews', 'reply_to_review', 'create_post', 'list_posts', 'get_insights']
      account_id:
        type: "string"
        description: "Google Business account ID — for list_locations, list_reviews, reply_to_review, create_post, list_posts, get_insights"
        default: ""
      location_id:
        type: "string"
        description: "Location ID — for get_location, list_reviews, reply_to_review, create_post, list_posts, get_insights"
        default: ""
      review_id:
        type: "string"
        description: "Review ID — for reply_to_review"
        default: ""
      reply_text:
        type: "string"
        description: "Reply text — for reply_to_review"
        default: ""
      post_body:
        type: "string"
        description: "Text content for the post — for create_post"
        default: ""
      post_media_url:
        type: "string"
        description: "Media URL to attach to the post — for create_post"
        default: ""
      post_call_to_action_type:
        type: "string"
        description: "Call-to-action button type — for create_post"
        enum: ['LEARN_MORE', 'BOOK', 'ORDER', 'SHOP', 'SIGN_UP', 'CALL']
        default: ""
      post_call_to_action_url:
        type: "string"
        description: "Call-to-action button URL — for create_post"
        default: ""
      start_date:
        type: "string"
        description: "Start date (YYYY-MM-DD) — for get_insights"
        default: ""
      end_date:
        type: "string"
        description: "End date (YYYY-MM-DD) — for get_insights"
        default: ""
      metric_requests:
        type: "string"
        description: "Comma-separated metrics — for get_insights (e.g. QUERIES_DIRECT,VIEWS_MAPS,ACTIONS_PHONE)"
        default: "QUERIES_DIRECT,QUERIES_INDIRECT,VIEWS_MAPS,VIEWS_SEARCH,ACTIONS_WEBSITE,ACTIONS_PHONE,ACTIONS_DRIVING_DIRECTIONS"
    required: [action]
---
# Google Business Profile

Manage Google Business Profile listings — reviews, posts, insights, and business info.

## Accounts & Locations
- **list_accounts** — List all Google Business Profile accounts accessible by the authenticated user.
- **list_locations** — List locations for an account. Provide `account_id`.
- **get_location** — Get details for a specific location. Provide `location_id`.

## Reviews
- **list_reviews** — List reviews for a location. Provide `account_id` and `location_id`.
- **reply_to_review** — Reply to a review. Provide `account_id`, `location_id`, `review_id`, and `reply_text`.

## Posts
- **create_post** — Create a local post. Provide `account_id`, `location_id`, and `post_body`. Optionally add `post_media_url`, `post_call_to_action_type`, and `post_call_to_action_url`.
- **list_posts** — List local posts for a location. Provide `account_id` and `location_id`.

## Insights
- **get_insights** — Get performance insights for a location. Provide `account_id`, `location_id`, `start_date`, `end_date`, and optionally `metric_requests` (comma-separated).

## Example: Reply to a review
```
action: reply_to_review
account_id: "123456789"
location_id: "987654321"
review_id: "AbCdEfGh"
reply_text: "Thank you for your feedback! We appreciate your business."
```

## Example: Create a post
```
action: create_post
account_id: "123456789"
location_id: "987654321"
post_body: "We're excited to announce our new spring menu! Stop by and try it today."
post_call_to_action_type: LEARN_MORE
post_call_to_action_url: "https://example.com/spring-menu"
```

## Example: Get insights
```
action: get_insights
account_id: "123456789"
location_id: "987654321"
start_date: "2026-01-01"
end_date: "2026-03-01"
metric_requests: "QUERIES_DIRECT,VIEWS_MAPS,ACTIONS_PHONE"
```
