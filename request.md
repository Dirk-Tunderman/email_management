### send-email route
["POST"]

```json
[
    "email_data": [
        {
            "email_recipient": "email placeholder",
            "subjectline": "subjcet of the email",
            "email_content": "content of the email",
            "time_zone": "time zone for the target recipient",
        },
    ]
]
```

https://{url}/send_email

### recieve_email
["GET"]

url query: size -> size of how many emails you want to fetch

https://{url}/rerecieve_email?size={value}


### reply-to-email

["POST"]

```json
{
    "sender":"the one sending the reply, email address",
    "reciever": "the one recieving a reply, email address",
    "reply": {
        "subject":"subject of the reply",
        "body":"body of the reply"
    },
    "time_zone": "time zone of the reciever"
}
```

request url : https://{url}/reply-to-email
