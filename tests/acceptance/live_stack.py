#!/usr/bin/env python3
"""Real HTTP acceptance for an explicitly local, development-fixture deployment.

Stdlib-only for use in native or Docker environments. This never uses real
credentials or devices; it refuses non-loopback destinations and mutates only
SIMULATED commands, synthetic notes/strategies/reports.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class API:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None
        self.timings = []

    def call(self, method, path, body=None, headers=None, csrf=True):
        headers = {"Accept":"application/json", **(headers or {})}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if csrf and self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        payload = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base+path, data=payload, headers=headers, method=method)
        start = time.perf_counter()
        try:
            response = self.opener.open(request, timeout=90)
        except urllib.error.HTTPError as exc:
            response = exc
        raw = response.read()
        elapsed = time.perf_counter()-start
        self.timings.append({"method":method,"path":path,"status":response.status,"elapsed_s":round(elapsed,4)})
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw.decode(errors="replace")
        return response.status, value, dict(response.headers)

    def data(self, path, method="GET", body=None, expected=200, headers=None):
        status, result, _ = self.call(method, path, body, headers)
        assert status == expected, (path,status,result)
        assert isinstance(result, dict) and "data" in result, (path,result)
        return result["data"]

    def login(self, role="admin"):
        result = self.data("/api/v1/auth/login", "POST", {"username":role,"password":"development-only"})
        self.csrf = result["csrf_token"]
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url",default="http://127.0.0.1:8000")
    parser.add_argument("--development-fixture",action="store_true",required=True)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--skip-commands",action="store_true")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1","localhost","::1"} or parsed.username or parsed.password:
        raise SystemExit("Refusing non-loopback or credentialed URL; explicit local test fixture only")
    api = API(args.base_url)
    checks = []
    def check(name, fn):
        started = time.perf_counter()
        try:
            detail = fn()
            checks.append({"name":name,"status":"passed","duration_s":round(time.perf_counter()-started,3),"detail":detail})
        except Exception as exc:
            checks.append({"name":name,"status":"failed","duration_s":round(time.perf_counter()-started,3),"error":str(exc),"trace":traceback.format_exc()})
        print(json.dumps(checks[-1],ensure_ascii=False),flush=True)

    def health_auth():
        assert api.call("GET","/health/ready")[0] == 200
        assert api.call("GET","/api/v1/devices")[0] == 401
        api.login()
        assert api.call("PATCH","/api/v1/settings",{},csrf=False)[0] == 403
        assert api.call("PATCH","/api/v1/settings",{},headers={"Origin":"https://attacker.invalid"})[0] == 403
        return {"authenticated":True,"csrf":"enforced","origin":"enforced"}
    check("live_health_auth_csrf_origin",health_auth)

    def campus():
        campuses=api.data("/api/v1/campuses")
        buildings=api.call("GET","/api/v1/buildings?limit=500")[1]
        spaces=api.call("GET","/api/v1/spaces?limit=500")[1]
        devices=api.call("GET","/api/v1/devices?limit=500")[1]
        assert len(campuses)==3
        assert buildings["meta"]["total"]==136
        assert spaces["meta"]["total"]==603
        assert devices["meta"]["total"]>=680
        assert all(x["source_mode"]=="SIMULATED" for x in devices["data"] if x["id"].startswith("SIM-"))
        return {"campuses":len(campuses),"buildings":136,"spaces":603,"devices":devices["meta"]["total"]}
    check("full_campus_reference_and_simulated_population",campus)

    def routes():
        paths=("overview","topology","assets/manifest","energy/summary","energy/breakdown","energy/balance","carbon/summary","cost/summary","carbon/factors","tariffs","forecasts","strategies","commands","alarms","reports","audit","settings","system/status")
        for path in paths:
            api.data("/api/v1/"+path)
        status=api.data("/api/v1/system/status")
        assert status["database"]["dialect"]=="postgresql"
        assert status["physical_control"]["enabled"] is False
        return {"routes":len(paths),"database":"postgresql","physical_control":False}
    check("api_routes_and_physical_gate",routes)

    def role_guard():
        viewer=API(args.base_url)
        viewer.login("viewer")
        for path in ("devices","commands","reports"):
            assert viewer.call("POST","/api/v1/"+path,{})[0]==403
        viewer.data("/api/v1/auth/logout","POST")
        assert viewer.call("GET","/api/v1/auth/me")[0]==401
        return {"viewer_mutations":"denied","logout":"revoked"}
    check("viewer_rbac_and_logout",role_guard)

    def report():
        row=api.data("/api/v1/reports","POST",{"name":"QA live acceptance "+uuid4().hex[:8],"type":"energy"},201)
        read=api.data("/api/v1/reports/"+row["id"])
        assert read["content"]==row["content"]
        status,csv,headers=api.call("GET","/api/v1/reports/"+row["id"]+"/export?format=csv")
        assert status==200 and "attachment" in (headers.get("Content-Disposition") or headers.get("content-disposition") or "")
        assert "SIMULATED" in str(csv)
        return {"report_id":row["id"],"source_mode":row["source_mode"],"snapshot_verified":True}
    check("report_persistence_and_export",report)

    def shadow():
        campuses=api.data("/api/v1/campuses")
        before=api.call("GET","/api/v1/commands?limit=1")[1]["meta"]["total"]
        strategy=api.data("/api/v1/strategies","POST",{"name":"QA live shadow "+uuid4().hex[:8],"campus_id":campuses[0]["id"],"target_reduction_pct":1.0,"max_devices":3},201)
        evaluation=api.data("/api/v1/strategies/"+strategy["id"]+"/evaluate","POST",{})
        assert evaluation["dispatch_performed"] is False
        assert evaluation["source_mode"]=="SIMULATED"
        approved=api.data("/api/v1/strategies/"+strategy["id"]+"/approve","POST",{"note":"QA approves shadow only; no automatic dispatch"})
        assert approved["status"]=="approved"
        after=api.call("GET","/api/v1/commands?limit=1")[1]["meta"]["total"]
        assert before==after
        return {"strategy_id":strategy["id"],"approval_dispatched":False}
    check("shadow_evaluate_approve_without_implicit_dispatch",shadow)

    if not args.skip_commands:
        def commands():
            devices=api.data("/api/v1/devices?limit=500&source_mode=SIMULATED&status=online")
            candidates=[d for d in devices if d["kind"]=="smart_plug" and d["allow_control"] and d["commissioned"] and not d["critical"] and d["latest"] and d["latest"]["quality"]=="good"]
            assert len(candidates)>=4
            result=[]
            for device,scenario,terminal in zip(candidates,["success","reject","fail","timeout"],["verified","rejected","failed","timed_out"]):
                key="qa-live-"+uuid4().hex
                body={"device_id":device["id"],"action":"shed","expires_in_seconds":8 if scenario=="timeout" else 30,"reason":"Local acceptance simulated "+scenario,"simulation_scenario":scenario}
                command=api.data("/api/v1/commands","POST",body,201,{"Idempotency-Key":key})
                retry=api.data("/api/v1/commands","POST",body,200,{"Idempotency-Key":key})
                assert retry["id"]==command["id"]
                assert api.call("POST","/api/v1/commands",body|{"action":"restore"},{"Idempotency-Key":key})[0]==409
                deadline=time.monotonic()+40
                while command["status"] not in {"verified","rejected","failed","timed_out"} and time.monotonic()<deadline:
                    time.sleep(.3)
                    command=api.data("/api/v1/commands/"+command["id"])
                assert command["status"]==terminal, command
                if terminal=="verified":
                    assert command["result"]["simulated"] is True and command["result"]["voltage_absence_proven"] is False
                    evidence=command["history"][-1]["evidence"]
                    assert evidence.get("telemetry_id") or evidence.get("observation_id"), "No persisted correlated feedback evidence"
                result.append({"id":command["id"],"scenario":scenario,"terminal":terminal})
            return result
        check("worker_command_state_machine_ttl_replay_feedback",commands)

    report={"started_at":datetime.now(timezone.utc).isoformat(),"base_url":args.base_url,"fixture":"explicit development only","checks":checks,"timings":api.timings,"passed":sum(x["status"]=="passed" for x in checks),"failed":sum(x["status"]=="failed" for x in checks)}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding="utf-8")
    print(json.dumps({"passed":report["passed"],"failed":report["failed"],"output":str(args.output) if args.output else None}),flush=True)
    return int(bool(report["failed"]))

if __name__=="__main__":
    sys.exit(main())
