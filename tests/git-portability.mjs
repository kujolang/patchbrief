// Real Git/Kujo contract; intentionally grants no shell-execution capability.
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm,access} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
const binary=process.env.KUJO_BIN;
assert.ok(binary,'Set KUJO_BIN to the native runtime');
const root=resolve('.'),directory=await mkdtemp(join(tmpdir(),'patchbrief portability ')),repo=join(directory,'repository');
const flags=['--untrusted','--allow-fs-read','--allow-process-exec','--allow-env-read','--allow-clock'];
try {
 await mkdir(repo);
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{encoding:'utf8'});
 git('init','-q','-b','portable');git('config','user.name','Test');git('config','user.email','test@example.com');git('config','core.autocrlf','false');
 const unusual="café ' & $(touch injected).txt";
 await writeFile(join(repo,unusual),'before\n');git('add','--',unusual);git('commit','-qm','initial');
 await writeFile(join(repo,unusual),'after\n');await writeFile(join(repo,'untracked.md'),'new\n');
 const run=(entry,args=[],cwd=repo,extra={})=>spawnSync(binary,['run',entry,...flags,'--',...args],{cwd,env:{...process.env,KUJO_MODULE_PATH:root,...extra},encoding:'utf8',timeout:30000,maxBuffer:2*1024*1024});
 for(const interpreter of [false,true]) {
  if(interpreter)flags.push('--interpreter');
  const result=run(join(root,'patchbrief.kujo'),['summarize','--format','json']);
  assert.equal(result.status,0,result.stdout+result.stderr);
  const summary=JSON.parse(result.stdout);assert.equal(summary.summary.files_changed,2);assert.equal(summary.branch,'portable');
  assert.ok(summary.files.some(f=>f.path===unusual));assert.equal(summary.summary.lines_added,1);assert.equal(summary.summary.lines_removed,1);
  const helper=join(directory,'probe.kujo');
  await writeFile(helper,`from src.git import file_diff, recent_commits\nprint(to_json({"diff":file_diff(${JSON.stringify(unusual)}),"commits":recent_commits(1)}))\n`);
  const probe=run(helper);assert.equal(probe.status,0,probe.stderr);const detail=JSON.parse(probe.stdout);
  assert.ok(detail.diff.includes('+after'));assert.equal(detail.commits.length,1);assert.ok(detail.commits[0].endsWith('initial'));
  await assert.rejects(access(join(repo,'injected')));
  const handoff=run(join(root,'patchbrief.kujo'),['handoff','--format','json']);assert.equal(handoff.status,0,handoff.stderr);
  assert.match(JSON.parse(handoff.stdout).generated_at,/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/);
  const outside=run(join(root,'patchbrief.kujo'),['summarize','--format','json'],directory);
  assert.equal(outside.status,1);assert.deepEqual(JSON.parse(outside.stdout),{error:true,message:'Not a git repository. Run patchbrief inside a git repo.'});
  const invalidIndex=join(directory,'invalid-index');await writeFile(invalidIndex,'invalid');
  const broken=run(join(root,'patchbrief.kujo'),['summarize','--format','json'],repo,{GIT_INDEX_FILE:invalidIndex});
  assert.equal(broken.status,1);assert.equal(JSON.parse(broken.stdout).message,'Failed to inspect git working tree.');
 }
 console.log('PASS: VM and interpreter Git review, literal filenames, UTC handoff, non-repository and corrupt-index errors without shell authority');
} finally {await rm(directory,{recursive:true,force:true});}
