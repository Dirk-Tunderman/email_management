# from flask import Flask, request, jsonify
# from dotenv import load_dotenv
# import os
# from src.email_management.sender import entrypoint, send_reply
# from reciever import main
# from flask_cors import CORS

# load_dotenv()

# # init and config
# app = Flask(__name__)
# CORS(app)
# app.config["DEBUG"] = os.environ.get("FLASK_DEBUG") == "True"


# @app.route("/")
# def hello():
#     return "Hello World!"


# @app.route("/send_email", methods=["POST"])
# def send_email():
#     try:
#         entrypoint(request.get_json()["email_data"])
#         return jsonify({"message": "Email sent successfully"}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route("/recieve_email", methods=["GET"])
# def recieve_email():
#     print(f"\n=== Received Recieve Request ===")
#     try:
#         emails = main(size=int(request.args.get("size")))
#         return jsonify({"emails": emails}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# import json
# import re
# import traceback
# from src.email_management.src.lib.supabase_client import supabase_client


# @app.route("/reply-to-email", methods=["POST"])
# def reply_email():
#     try:
#         data = request.get_json()
#         print(f"\n=== Received Reply Request ===")
#         print(f"Data: {json.dumps(data, indent=2)}")
        
#         # Find the original email based on subject and recipient
#         clean_subject = re.sub(r'^(Re:\s*)+', '', data["reply"]["subject"], flags=re.IGNORECASE)
#         original_email = supabase_client.client.from_("received_email") \
#             .select("*") \
#             .eq("sender", data["receiver"]) \
#             .ilike("subject", f"%{clean_subject}%") \
#             .order("created_at", desc=True) \
#             .limit(1) \
#             .execute()

#         if not original_email.data:
#             return jsonify({"error": "Original email not found"}), 404

#         res = send_reply(
#             sender=data["sender"],
#             recipient=data["receiver"],
#             subject=data["reply"]["subject"],
#             body=data["reply"]["body"],
#             original_email=original_email.data[0],
#             time_zone=data.get("time_zone", "Europe/Amsterdam")
#         )
        
#         if res[0]:  # Check if send_reply was successful
#             return jsonify({"message": "Email sent successfully"}), 200
#         else:
#             return jsonify({"error": res[1]}), 500
            
#     except Exception as e:
#         print(f"\nERROR in reply_email: {str(e)}")
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 8080))
#     app.run(host="0.0.0.0", port=port)
