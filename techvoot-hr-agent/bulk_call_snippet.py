@app.route('/api/start_queue', methods=['POST'])
@login_required
def api_start_queue():
    """Start bulk calling queue"""
    try:
        pending_candidates = database.get_pending_candidates()
        
        if not pending_candidates:
            return jsonify({"success": False, "message": "No pending candidates found"})
            
        results = {
            "total": len(pending_candidates),
            "initiated": 0,
            "failed": 0,
            "errors": []
        }
        
        client = Client(Config.OMNIDIMENSION_API_KEY)
        
        for candidate in pending_candidates:
            try:
                # Dispatch call
                client.call.dispatch_call(
                    agent_id=int(Config.OMNIDIMENSION_AGENT_ID),
                    to_number=candidate['phone']
                )
                
                # Log attempt
                database.log_call(candidate['id'], "initiated", 0, "Bulk call initiated")
                results["initiated"] += 1
                
            except Exception as e:
                print(f"Failed to call {candidate['name']}: {e}")
                results["failed"] += 1
                results["errors"].append(f"{candidate['name']}: {str(e)}")
                
        return jsonify({"success": True, "results": results})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
