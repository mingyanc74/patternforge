// Development-only fixture: not imported by the production index or build.
import React from "react";
import { createRoot } from "react-dom/client";
import App from "../src/App";
import "../src/styles.css";
import type { Job } from "../src/api";
const now = Date.now();
const expiredConnection = new URLSearchParams(location.search).get("expired") === "1";
const connection = {id:"10000000-0000-4000-8000-000000000001",bucket:"clearflow-ui-fixture",region:"ap-southeast-2",expires_at:new Date(now+86400000).toISOString()};
const columns = ["ID","Name","Email","Description"].map(name => ({name,type:"string"}));
const rows = Array.from({length:12},(_,i) => ({ID:String(i+1).padStart(3,"0"),Name:["Alice Chen","John Doe","Jane Smith","Sam Wilson"][i%4],Email:"user"+i+"@example.com",Description:"Order ORD-"+(1000+i)}));
const inspection:Job = {id:"20000000-0000-4000-8000-000000000001",kind:"inspect",source_key:"customers_october.csv",connection_id:connection.id,status:"SUCCESS",stage:"COMPLETED",progress:100,attempt:1,cancel_requested:false,created_at:new Date(now).toISOString(),started_at:null,finished_at:new Date(now).toISOString(),result_expires_at:new Date(now+86400000).toISOString(),result_available:false,error:null,metadata:{columns,preview:rows}};
const jobs:Job[] = Array.from({length:7},(_,i) => {
  const status = (["SUCCESS","SUCCESS","FAILED","SUCCESS","CANCELLED","RUNNING","SUCCESS"] as Job["status"][])[i];
  const operation = (["regex_extract","normalize","regex_extract","regex_replace","regex_extract","regex_replace","regex_replace"] as const)[i],created=now-i*7200000;
  return {...inspection,id:"30000000-0000-4000-8000-"+String(i+1).padStart(12,"0"),kind:"transform",bucket:connection.bucket,region:connection.region,operation,
    source_key:i%2 ? "customers_october.csv" : "reports/orders_2026.xlsx",sheet:i%2 ? "" : "Orders",status,stage:status==="RUNNING" ? "TRANSFORMING" : status==="SUCCESS" ? "COMPLETED" : status,
    progress:status==="RUNNING" ? 65 : status==="SUCCESS" ? 100 : 35,created_at:new Date(created).toISOString(),started_at:new Date(created+1000).toISOString(),finished_at:status==="RUNNING" ? null : new Date(created+12000).toISOString(),
    result_expires_at:new Date(i===6 ? now-1000 : now+86400000).toISOString(),result_available:status==="SUCCESS",
    config:{operation,inspection_id:inspection.id,prompt:operation==="normalize" ? "Trim spaces and convert to lowercase" : operation==="regex_extract" ? "Extract the order ID" : "Find email addresses",target_columns:[operation==="normalize" ? "Name" : operation==="regex_extract" ? "Description" : "Email"],replacement:"REDACTED",new_column:"order_id",sheet:i%2 ? "" : "Orders",delimiter:",",encoding:"UTF-8"},
    metadata:{columns,row_count:12,changed_cells:{Email:12},partitions:8,cache_hit:false},
    plan:{operation,pattern:operation==="normalize" ? null : "email-pattern-ui-fixture",steps:operation==="normalize" ? ["trim","lowercase"] : [],explanation:"Fixture rule for UI verification only."},
    error:status==="FAILED" ? {code:"RULE_REJECTED",message:"The generated rule could not be used safely."} : null};
});
// Additive dataset-lifetime scenario. Keep the original jobs/inspection stores.
inspection.dataset_available = true;
inspection.dataset_expires_at = new Date(now+86400000).toISOString();
inspection.bucket = connection.bucket;
inspection.region = connection.region;
inspection.source_type = "amazon_s3";
inspection.config = {delimiter:",",encoding:"UTF-8",sheet:""};
if(expiredConnection) connection.expires_at = new Date(now-1000).toISOString();
const realFetch = window.fetch.bind(window);
window.fetch = async (input,init) => {
  const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url,location.origin);
  if (!url.pathname.startsWith("/api/")) return realFetch(input,init);
  const path=url.pathname.slice(4),body=init?.body ? JSON.parse(String(init.body)) : {};
  let output:unknown={},status=200;
  if(expiredConnection && ((path.includes("/files") && path.startsWith("/s3/")) || path==="/files/inspect"))
    return new Response(JSON.stringify({error:{code:"CONNECTION_EXPIRED",message:"Fixture connection expired. Imported datasets are still available."}}),{status:410,headers:{"Content-Type":"application/json"}});
  if(path==="/bootstrap") output={csrf_token:"fixture-only",access_required:new URLSearchParams(location.search).get("gate")==="1",llm_configured:true,limits:{preview_rows:100,max_page_rows:500,max_file_bytes:2147483648,max_excel_bytes:104857600,result_ttl_hours:24,credential_ttl_hours:1,dataset_ttl_hours:24}};
  else if(path==="/datasets") output={datasets:[inspection]};
  else if(path==="/health") output={status:"ready",services:{database:true,queue:true,worker:true,spark:true,llm_configured:true}};
  else if(path==="/s3/connections") output=init?.method==="POST" ? {...connection,bucket:body.bucket,region:body.region} : {connections:expiredConnection ? [] : [connection]};
  else if(path.includes("/files") && path.startsWith("/s3/")) output={files:[{key:"customers_october.csv",size:2048,modified:new Date(now).toISOString(),supported:true},{key:"reports/orders_2026.xlsx",size:4096,modified:new Date(now).toISOString(),supported:true},{key:"readme.txt",size:120,modified:new Date(now).toISOString(),supported:false}],next_cursor:null};
  else if(path==="/files/inspect") { Object.assign(inspection,{source_key:body.source_key,config:body,metadata:body.source_key.endsWith(".xlsx") && !body.sheet ? {sheets:["Customers","Orders"],requires_sheet:true} : {columns,preview:rows,sheet:body.sheet}}); output=inspection; status=202; }
  else if(path==="/jobs" && init?.method==="POST") {
    const next:Job={...jobs[0],id:crypto.randomUUID(),source_key:body.source_key,config:body,operation:body.operation,status:"QUEUED",progress:0,stage:"QUEUED",created_at:new Date().toISOString(),started_at:null,finished_at:null,result_available:false,error:null};
    jobs.unshift(next); output=next; status=202;
    setTimeout(()=>{if(next.status!=="CANCELLED") Object.assign(next,{status:"RUNNING",started_at:new Date().toISOString(),progress:40,stage:"READING"});},1500);
    setTimeout(()=>{if(next.status!=="CANCELLED") Object.assign(next,{status:"SUCCESS",finished_at:new Date().toISOString(),progress:100,stage:"COMPLETED",result_available:true});},7000);
  } else if(path==="/jobs") {
    const query=(url.searchParams.get("search")||"").toLowerCase(),filter=url.searchParams.get("status"),page=Number(url.searchParams.get("page")||1),limit=Number(url.searchParams.get("limit")||50);
    const list=jobs.filter(j=>(!query||(j.id+" "+j.source_key).toLowerCase().includes(query))&&(!filter||(filter==="expired" ? j.status==="SUCCESS"&&new Date(j.result_expires_at!).getTime()<now : j.status===filter)));
    output={jobs:list.slice((page-1)*limit,page*limit),total:list.length,page,page_size:limit,has_next:page*limit<list.length};
  } else if(path.startsWith("/jobs/")) {
    const id=path.split("/")[2],item=jobs.find(j=>j.id===id)||inspection;
    if(path.endsWith("/cancel")) Object.assign(item,{status:"CANCELLED",stage:"CANCELLED",finished_at:new Date().toISOString(),cancel_requested:true});
    if(path.endsWith("/results")) { const offset=Number(url.searchParams.get("cursor")||0),data=rows.map(row=>({...row,Email:"REDACTED"})); output={rows:data.slice(offset,offset+5),columns,total_rows:12,offset,returned_rows:Math.min(5,12-offset),next_cursor:offset+5<12 ? String(offset+5):null,version:"ui-fixture"}; }
    else output=item;
  } else if(init?.method==="DELETE") status=204;
  else {status=404;output={error:{code:"FIXTURE_ROUTE_MISSING",message:"Route not covered by UI fixture."}};}
  return new Response(status===204 ? null : JSON.stringify(output),{status,headers:{"Content-Type":"application/json"}});
};
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
