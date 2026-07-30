from html import escape
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description='Generate the TUSK deep-zoom architecture SVG.')
parser.add_argument('output', nargs='?', default='architecture-deep-zoom.svg', help='Output SVG path (default: repository root architecture-deep-zoom.svg)')
args = parser.parse_args()
OUT = Path(args.output)

parts=[]
def add(s): parts.append(s)

def title(text): return f"<title>{escape(text, quote=False)}</title>"

def multiline(x,y,lines,cls='detail',line_h=18,anchor='start'):
    spans=[]
    for i,line in enumerate(lines):
        dy='0' if i==0 else str(line_h)
        spans.append(f'<tspan x="{x}" dy="{dy}">{escape(line, quote=False)}</tspan>')
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">' + ''.join(spans) + '</text>'

def box(gid,x,y,w,h,label,subtitle='',kind='module',evidence='',level=2,rx=28,extra_class='',badge=''):
    cls=f'node {kind} level-{level} {extra_class}'.strip()
    add(f'<g id="{gid}" class="{cls}" transform="translate({x} {y})">')
    if evidence: add(title(evidence))
    add(f'<rect x="0" y="0" width="{w}" height="{h}" rx="{rx}"/>')
    label_cls=f'label l{level}'
    add(f'<text x="{w/2}" y="{55 if level<=2 else 32}" class="{label_cls}" text-anchor="middle">{escape(label, quote=False)}</text>')
    if subtitle:
        add(f'<text x="{w/2}" y="{88 if level<=2 else 54}" class="subtitle s{level}" text-anchor="middle">{escape(subtitle, quote=False)}</text>')
    if badge:
        add(f'<text x="{w-16}" y="18" class="badge" text-anchor="end">{escape(badge, quote=False)}</text>')
    return lambda: add('</g>')

def card(gid,x,y,w,h,label,lines,evidence='',kind='class',inferred=False,badge='',extra_class=''):
    classes=' '.join(item for item in [('inferred' if inferred else ''), extra_class] if item)
    end=box(gid,x,y,w,h,label,'',kind,evidence,level=4,rx=14,badge=badge,extra_class=classes)
    add(multiline(14,46,lines,'micro',14))
    end()

def smallbox(gid,x,y,w,h,label,evidence='',kind='detail',inferred=False):
    cls='inferred' if inferred else ''
    end=box(gid,x,y,w,h,label,'',kind,evidence,level=5,rx=9,extra_class=cls)
    end()

def edge(gid,x1,y1,x2,y2,label='',kind='call',inferred=False,curve=None,marker=True):
    cls=f'edge {kind}' + (' inferred-edge' if inferred else '')
    if curve:
        d=f'M {x1} {y1} C {curve[0]} {curve[1]}, {curve[2]} {curve[3]}, {x2} {y2}'
        path=f'<path id="{gid}" class="{cls}" d="{d}"' + (' marker-end="url(#arrow)"' if marker else '') + '/>'
        add(path)
        if label:
            mx=(x1+x2+curve[0]+curve[2])/4; my=(y1+y2+curve[1]+curve[3])/4
            add(f'<text x="{mx}" y="{my-8}" class="edge-label" text-anchor="middle">{escape(label, quote=False)}</text>')
    else:
        add(f'<line id="{gid}" class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"' + (' marker-end="url(#arrow)"' if marker else '') + '/>')
        if label:
            add(f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-10}" class="edge-label" text-anchor="middle">{escape(label, quote=False)}</text>')

def group_start(gid,x=0,y=0,cls=''):
    add(f'<g id="{gid}" class="{cls}" transform="translate({x} {y})">')
def group_end(): add('</g>')

add('''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" width="7200" height="4400" viewBox="0 0 7200 4400" role="img" aria-labelledby="diagram-title diagram-desc">
<title id="diagram-title">TUSK deep-zoom software architecture recovered from source code</title>
<desc id="diagram-desc">A recursively nested architecture map of the TUSK desktop assistant. Zoom into the main process, shells, kernel, agent engine, MCP adapters, host integration, providers, persistence, and implementation details.</desc>
<metadata>
Repository: https://github.com/vovka/tusk
Source revision inspected: 0e8f2d7760ea98ed28f5e78462b9adc5c536cb09
Generated from production code, manifests, deployment files, and tests. Existing architecture documentation and diagrams were intentionally excluded from evidence.
</metadata>
<defs>
  <marker id="arrow" markerWidth="14" markerHeight="14" refX="11" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L12,5 L0,10 z" fill="context-stroke"/></marker>
  <style>
    svg { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .canvas-title { font-size:86px; font-weight:800; fill:#14213d; letter-spacing:-2px; }
    .canvas-subtitle { font-size:28px; fill:#52616b; }
    .node rect { stroke-width:4; fill:#fff; stroke:#334155; }
    .system rect { fill:#f8fbff; stroke:#1d4ed8; stroke-width:8; }
    .application rect { fill:#edf5ff; stroke:#2563eb; }
    .process rect { fill:#eefcf6; stroke:#16865a; }
    .module rect { fill:#ffffff; stroke:#64748b; }
    .shell rect { fill:#fff8e8; stroke:#b7791f; }
    .kernel rect { fill:#f4efff; stroke:#7048b8; }
    .agent rect { fill:#eef8ff; stroke:#1677a6; }
    .provider rect { fill:#fff1f1; stroke:#c24141; }
    .adapter rect { fill:#eefcf6; stroke:#16865a; }
    .class rect { fill:#ffffff; stroke:#64748b; stroke-width:2.4; }
    .detail rect { fill:#ffffff; stroke:#94a3b8; stroke-width:1.5; }
    .datastore rect { fill:#fff7db; stroke:#b7791f; }
    .external rect { fill:#f2f4f8; stroke:#475569; }
    .queue rect { fill:#f7f0ff; stroke:#7c3aed; }
    .summarized rect { stroke-dasharray:14 10; fill:#fafafa; }
    .inferred rect { stroke:#8b5cf6; stroke-dasharray:14 9; fill:#faf7ff; }
    .label { fill:#172033; font-weight:750; dominant-baseline:middle; }
    .l1 { font-size:120px; }
    .l2 { font-size:30px; }
    .l3 { font-size:7.5px; }
    .l4 { font-size:1.875px; }
    .l5 { font-size:0.46875px; }
    .subtitle { fill:#556272; }
    .s1 { font-size:28px; }
    .s2 { font-size:9px; }
    .s3 { font-size:2.3px; }
    .s4 { font-size:0.6px; }
    .s5 { font-size:0.16px; }
    .micro { font-size:1.4px; fill:#334155; }
    .nano { font-size:0.35px; fill:#475569; }
    .badge { font-size:2.4px; font-weight:700; fill:#7c3aed; }
    .edge { fill:none; stroke:#475569; stroke-width:6; opacity:.9; }
    .edge.call { stroke:#475569; }
    .edge.data { stroke:#b7791f; }
    .edge.mcp { stroke:#16865a; }
    .edge.audio { stroke:#b45309; }
    .edge.http { stroke:#c24141; }
    .edge.control { stroke:#7048b8; }
    .edge-label { font-size:18px; font-weight:650; fill:#334155; paint-order:stroke; stroke:#f6f8fb; stroke-width:8; stroke-linejoin:round; }
    .micro-edge { fill:none; stroke:#64748b; stroke-width:2; marker-end:url(#arrow); }
    .micro-edge-label { font-size:0.8px; fill:#475569; paint-order:stroke; stroke:white; stroke-width:0.4; }
    .inferred-edge { stroke:#8b5cf6; stroke-dasharray:18 12; }
    .actor-shape { fill:#fff; stroke:#14213d; stroke-width:8; }
    .actor-label { font-size:58px; font-weight:800; fill:#14213d; }
    .actor-detail { font-size:22px; fill:#52616b; }
    .legend-text { font-size:17px; fill:#334155; }
    .legend-title { font-size:26px; font-weight:800; fill:#14213d; }
    .scope-note { font-size:15px; fill:#64748b; }
  
    .low-level-edge { stroke-width:3; opacity:.58; }
    .low-level-label { font-size:12px; opacity:.68; }
</style>
</defs>
<rect width="7200" height="4400" fill="#f6f8fb"/>
<text x="180" y="125" class="canvas-title">TUSK — source-recovered architecture</text>
<text x="185" y="185" class="canvas-subtitle">One deployment, one central kernel, configurable interaction shells, MCP child-process adapters, optional Codex backends, and explicit host integration.</text>
''')

# Actor
add('<g id="actor-user" transform="translate(80 1510)">')
add(title('Human user interacting through microphone, CLI, tray controls, and the GNOME desktop. Evidence: shells/voice, shells/cli, shells/tray.'))
add('<circle cx="290" cy="145" r="95" class="actor-shape"/><path d="M115 570 Q290 300 465 570 Z" class="actor-shape"/>')
add('<text x="290" y="690" text-anchor="middle" class="actor-label">User</text>')
add('<text x="290" y="735" text-anchor="middle" class="actor-detail">voice • text • tray</text>')
add('</g>')

# Main system boundary
end_system=box('system-tusk',850,250,5500,3900,'TUSK desktop-assistant system','single application deployment + child processes + observability service','system','docker-compose.yml; main.py; shell_loader.py; tusk/kernel/core/startup.py; adapters/*/adapter.json',level=1,rx=54)

# Main container
end_main=box('deployable-tusk-container',250,260,3500,3050,'TUSK application container','Python 3.11 process; default shell: voice','application','Dockerfile; docker-compose.yml; main.py',level=2,rx=40)

# Composition root
end_comp=box('module-composition-root',100,150,3300,330,'Composition root','configuration → providers → kernel → shells','module','main.py; shell_loader.py; tusk/kernel/core/startup.py; tests/test_shell_loader.py',level=3,rx=24)
card('class-main-entry',40,95,470,175,'main.py',['main()','_build_llm_registry()','_build_kernel()'],'main.py')
card('class-shell-loader',570,95,650,175,'ShellLoader',['start(); _run()','_build_voice()','_gatekeeper(); _wire_modes()'],'shell_loader.py; tests/test_shell_loader.py')
card('class-startup',1280,95,600,175,'startup.py',['build_kernel()','build_agent()','build_adapter_manager()'],'tusk/kernel/core/startup.py')
card('class-config',1940,95,560,175,'ConfigFactory',['env → Config','LLM slots; shells','audio; backend selection'],'tusk/shared/config/config_factory.py; .env.example')
card('class-status-tracer',2560,95,680,175,'Cross-cutting bootstrap',['StatusReporterHub','InterruptToken','TracerFactory → OTel / Null'],'main.py; tusk/shared/tracing/tracer_factory.py')
end_comp()

# Shells module
end_shells=box('module-shells',100,550,950,2000,'Interaction shells','all call KernelAPI.submit','shell','shells/; shell_loader.py',level=3,rx=24)
# Voice shell
end_voice=box('shell-voice',35,100,880,1280,'VoiceShell','real-time capture + queued command execution','shell','shells/voice/voice_shell.py; shells/voice/pipeline.py; shells/voice/command_worker.py',level=4,rx=18)
# voice internals row 1
smallbox('voice-audio-capture',35,95,115,120,'AudioCapture','shells/voice/stages/audio_capture.py')
smallbox('voice-utterance-detector',170,95,125,120,'UtteranceDetector','shells/voice/stages/utterance_detector.py')
smallbox('voice-transcriber',315,95,115,120,'Transcriber','shells/voice/stages/transcriber.py')
smallbox('voice-sanitizer',450,95,105,120,'Sanitizer','shells/voice/stages/sanitizer.py')
smallbox('voice-buffer',575,95,120,120,'TranscriptionBuffer','shells/voice/stages/transcription_buffer.py')
smallbox('voice-gatekeeper',715,95,125,120,'Gatekeeper','shells/voice/stages/gate/gatekeeper.py; shells/voice/playback_gate.py')
for i,(x1,x2) in enumerate([(150,170),(295,315),(430,450),(555,575),(695,715)]):
    add(f'<line class="micro-edge" x1="{x1}" y1="155" x2="{x2}" y2="155"/>')
# queue and worker
smallbox('voice-capture-thread',35,270,185,140,'capture thread','VoicePipeline._capture_into()','queue')
smallbox('voice-utterance-queue',255,270,180,140,'Queue[Utterance]','queue.Queue','queue')
smallbox('voice-consumer',470,270,170,140,'pipeline consumer','_consume(); _dispatch()','queue')
smallbox('voice-command-worker',675,270,165,140,'CommandWorker','enqueue(); _run(); _execute()','queue')
add('<line class="micro-edge" x1="220" y1="340" x2="255" y2="340"/><line class="micro-edge" x1="435" y1="340" x2="470" y2="340"/><line class="micro-edge" x1="640" y1="340" x2="675" y2="340"/>')
# speech output
smallbox('voice-chunked-speaker',100,480,190,145,'ChunkedSpeaker','shells/voice/stages/chunked_speaker.py')
smallbox('voice-speech-playback',345,480,190,145,'SpeechPlayback','shells/voice/stages/speech_playback.py')
smallbox('voice-echo-filter',590,480,190,145,'EchoFilter','shells/voice/stages/echo_filter.py')
add('<line class="micro-edge" x1="290" y1="552" x2="345" y2="552"/><line class="micro-edge" x1="535" y1="552" x2="590" y2="552"/>')
# mode gates
smallbox('voice-gatekeeper-slot',100,705,190,145,'GatekeeperSlot','swap base / mode gate','detail')
smallbox('voice-stop-gatekeeper',345,705,190,145,'StopGatekeeper','dictation/coding stop routing','detail')
smallbox('voice-playback-gate',590,705,190,145,'PlaybackGate','speech-only interruption gate','detail')
add('<line class="micro-edge" x1="290" y1="778" x2="345" y2="778"/><line class="micro-edge" x1="535" y1="778" x2="590" y2="778"/>')
# methods note
add(multiline(45,970,['VoicePipeline.run(): capture thread → queue → STT → sanitize → buffer → gate → submit','CommandWorker runs KernelAPI.submit and TTS on a daemon worker; interrupt flushes queued work.'],'micro',16))
end_voice()

# small shells
card('shell-cli',35,1420,250,420,'CLIShell',['input("tusk> ")','submit(text)','print(reply)'],'shells/cli/cli_shell.py','class')
card('shell-emulator',315,1420,250,420,'EmulatorShell',['read TUSK_TRANSCRIPT','replay utterances','submit(utterance)'],'shells/emulator/emulator_shell.py','class')
card('shell-tray',595,1420,320,420,'TrayShell',['AppIndicator backend','attach TrayStatusSink','pause/resume/restart/stop'],'shells/tray/tray_shell.py; shells/tray/tray_status_sink.py','class')
add(multiline(45,1910,['ShellLoader starts every shell except the final one on daemon threads; tray is deliberately last/main-thread.'],'micro',14))
end_shells()

# Kernel module
end_kernel=box('module-kernel',1120,550,1050,2000,'Kernel + modes','serialized routing and mode state','kernel','tusk/kernel/core; tusk/kernel/modes; tests/kernel/test_kernel_api_gates.py',level=3,rx=24)
card('class-kernel-api',40,100,970,360,'KernelAPI',['submit(text, kind) — global lock','_route(): coding → dictation → command','request_interrupt(); start/stop modes','dictation_gate(); coding_gate()'],'tusk/kernel/core/kernel_api.py; tests/kernel/test_kernel_api_gates.py','class')
card('class-command-mode',40,510,440,300,'CommandMode',['AgentBackend.run(AgentRequest)','conversation session continuity','one-shot command session'],'tusk/kernel/core/command_mode.py','class')
card('class-mode-slot',530,510,480,300,'ModeSlot + ModeGate',['active state + router','start/process/stop callbacks','stop_gate LLM classification'],'tusk/kernel/modes/mode_slot.py; tusk/kernel/modes/mode_gate.py','class')
card('class-tool-runtime',40,860,440,330,'ToolRuntime',['attach DictationRouter','attach CodingRouter','register Start* + SwitchModel'],'tusk/kernel/tools/tool_runtime.py','class')
card('class-dictation-router',530,860,480,330,'DictationRouter',['dictation.process_segment','desktop.type_text / replace','stop_dictation'],'tusk/kernel/modes/dictation_router.py','class')
card('class-coding-router',40,1240,440,360,'CodingRouter',['coding.process_intent','EditApplicationStrategy.apply','EditorDriver automation','stop_coding_session'],'tusk/kernel/modes/coding_router.py','class')
card('class-edit-strategies',530,1240,480,360,'Coding edit path',['InputAutomationEditorDriver','VerifiedEditStrategy','LineAnchored → FullReplace fallback'],'tusk/kernel/modes/input_automation_editor_driver.py; tusk/kernel/modes/edit_strategies/','class')
add('<line class="micro-edge" x1="525" y1="280" x2="525" y2="510"/>')
add('<line class="micro-edge" x1="260" y1="810" x2="260" y2="860"/>')
add('<line class="micro-edge" x1="770" y1="810" x2="770" y2="860"/>')
add('<line class="micro-edge" x1="260" y1="1190" x2="260" y2="1240"/>')
add('<text x="525" y="1710" class="micro" text-anchor="middle">Mode routers intentionally reuse adapter tools through ToolRegistry; they are not direct adapter clients.</text>')
end_kernel()

# Agent module
end_agent=box('module-agent-engine',2240,550,1150,2000,'Agent execution engine','pluggable backend + built-in orchestrator','agent','tusk/kernel/agent; tusk/kernel/core/main_agent.py',level=3,rx=24)
card('class-backend-factory',40,100,1070,260,'AgentBackendFactory',['AGENT_BACKEND = tusk | codex_exec | codex_mcp','optional fallback → TuskAgentBackend'],'tusk/kernel/agent/backends/agent_backend_factory.py; tusk/shared/config/config_factory.py','class')
# built-in submodule
end_builtin=box('agent-built-in',40,410,710,1430,'Built-in TUSK backend','multi-profile recursive agent runtime','agent','tusk/kernel/core/main_agent.py; tusk/kernel/agent/agent_orchestrator.py; tusk/kernel/agent/agent_runtime.py',level=4,rx=18)
card('class-main-agent',25,75,660,210,'MainAgent',['conversation vs one-shot command','AgentOrchestrator.run()','share command results into conversation'],'tusk/kernel/core/main_agent.py','class')
card('class-orchestrator',25,330,660,260,'AgentOrchestrator',['profiles + ToolRegistry + Store','planner enrichment / runtime tool resolution','child run_agent delegation','tool sequence dispatcher'],'tusk/kernel/agent/agent_orchestrator.py','class')
card('class-agent-runtime',25,635,660,250,'AgentRuntime',['session event history','LLM tool-call loop','turn/repeat guards','done / failed / cancelled'],'tusk/kernel/agent/agent_runtime.py','class')
card('class-agent-profiles',25,930,310,330,'AgentProfiles',['conversation','command','planner','executor','default'],'tusk/kernel/core/agent_profiles.py','class')
card('class-agent-support',375,930,310,330,'Support components',['AgentChildRunner','AgentToolsetBuilder','OrchestratorToolDispatcher','Sequence Executor','ResultValidator'],'tusk/kernel/agent/','class',badge='summarized')
add('<line class="micro-edge" x1="355" y1="285" x2="355" y2="330"/><line class="micro-edge" x1="355" y1="590" x2="355" y2="635"/>')
end_builtin()
# Codex alternative cards
card('class-codex-exec-backend',790,410,320,430,'CodexExecBackend',['subprocess.run(codex exec …)','JSON result schema','timeout / exit handling'],'tusk/kernel/agent/backends/codex_exec_agent_backend.py','class')
card('class-codex-mcp-backend',790,890,320,430,'CodexMcpBackend',['persistent codex mcp-server','serialized turns','thread-id continuity','restart on stale thread'],'tusk/kernel/agent/backends/codex_mcp_agent_backend.py','class')
card('class-fallback-backend',790,1370,320,260,'FallbackBackend',['primary failure → built-in','selected at composition time'],'tusk/kernel/agent/backends/fallback_agent_backend.py','class')
add('<line class="micro-edge" x1="575" y1="360" x2="575" y2="410"/>')
add('<line class="micro-edge" x1="950" y1="360" x2="950" y2="410"/>')
end_agent()

# Infrastructure strip inside main
end_infra=box('module-shared-infrastructure',100,2630,3290,300,'Providers + shared infrastructure','factories, registries, MCP plumbing, status, logging, tracing, schemas','provider','tusk/providers; tusk/shared; requirements.txt',level=3,rx=22,badge='representative')
card('infra-llm',30,80,620,170,'LLM slots',['LLMRegistry → LLMProxy','ConfigurableLLMFactory','GroqLLM | OpenRouterLLM'],'main.py; tusk/shared/llm; tusk/providers/llm','class')
card('infra-audio',690,80,560,170,'Audio providers',['STTEngineFactory','GroqSTT | local WhisperSTT','GroqTTS'],'tusk/providers/stt; tusk/providers/tts','class')
card('infra-mcp',1290,80,600,170,'MCP client plumbing',['MCPClient','MCPStdioTransport','MCPToolProxy','AdapterEnvironmentBuilder'],'tusk/shared/mcp','class')
card('infra-status',1930,80,620,170,'Runtime services',['StatusReporterHub','ColorLogPrinter','InterruptToken','Config'],'tusk/shared/status; tusk/shared/logging; tusk/shared/interrupt; tusk/shared/config','class')
card('infra-tracing',2590,80,660,170,'Observability',['TracerFactory','OTelTracer / NullTracer','OTLPSpanExporter'],'tusk/shared/tracing; docker-compose.yml','class')
end_infra()

end_main()

# Adapter child processes zone
end_adapters=box('deployable-adapter-processes',3900,260,1250,2500,'Adapter child processes','hot-pluggable directories; MCP JSON-RPC 2.0 over stdio','process','tusk/kernel/core/adapter_manager.py; adapters/*/adapter.json; tusk/shared/mcp/mcp_client.py',level=2,rx=40)

# Gnome adapter
end_gnome=box('process-adapter-gnome',50,120,1150,900,'GNOME adapter','context + application + input + window tools','adapter','adapters/gnome/adapter.json; adapters/gnome/server.py; tests/adapters/test_gnome_server_mcp.py',level=3,rx=22)
card('gnome-mcp-server',30,90,300,180,'MCPStdioServer',['initialize','tools/list','tools/call'],'adapters/gnome/server.py; tusk/shared/mcp/mcp_stdio_server.py','class')
card('gnome-router',365,90,735,180,'GnomeToolRouter',['ApplicationTools • ClipboardTools • ContextTools','InputTools • WindowTools','ToolSchemaCatalog'],'adapters/gnome/gnome_tool_router.py','class')
card('gnome-app-tools',30,320,250,250,'Applications',['search .desktop files','Unix socket launch','xdg-open URI','poll wmctrl windows'],'adapters/gnome/app_catalog.py; adapters/gnome/tools/application_tools.py','class')
card('gnome-context',310,320,250,250,'Desktop context',['wmctrl -l -G','xdotool active window','available applications'],'adapters/gnome/gnome_context_provider.py','class')
card('gnome-input',590,320,250,250,'Input automation',['xdotool key/type','mouse move/click/drag/scroll'],'adapters/gnome/gnome_input_simulator.py','class')
card('gnome-clipboard',870,320,230,250,'Text + clipboard',['xclip or wl-copy/paste','replace recent text','BackSpace + type'],'adapters/gnome/gnome_clipboard_provider.py; adapters/gnome/gnome_text_paster.py','class')
add('<line class="micro-edge" x1="330" y1="180" x2="365" y2="180"/>')
for x in (155,435,715,985): add(f'<line class="micro-edge" x1="{x}" y1="270" x2="{x}" y2="320"/>')
add('<text x="575" y="700" class="micro" text-anchor="middle">Manifest marks GNOME as the primary desktop context source and exposes sequence-callable tools.</text>')
end_gnome()

# Coding adapter
end_coding=box('process-adapter-coding',50,1070,1150,430,'Coding adapter','session-scoped whole-buffer edit planning','adapter','adapters/coding/adapter.json; adapters/coding/server.py',level=3,rx=22)
card('coding-server',30,80,360,260,'CodingServer',['start_coding_session','process_intent','stop_coding_session','in-memory session buffers'],'adapters/coding/server.py','class')
card('coding-planner',430,80,330,260,'CodingEditPlanner',['LLM plans new buffer','returns replace operation'],'adapters/coding/coding_edit_planner.py; adapters/coding/server.py','class')
card('coding-schema',800,80,300,260,'Tool schema catalog',['3 hidden internal tools','MCP response payload'],'adapters/coding/coding_tool_schema_catalog.py','class')
add('<line class="micro-edge" x1="390" y1="210" x2="430" y2="210"/>')
end_coding()

# Dictation adapter
end_dict=box('process-adapter-dictation',50,1540,1150,430,'Dictation adapter','session-scoped segment accumulation','adapter','adapters/dictation/adapter.json; adapters/dictation/server.py',level=3,rx=22)
card('dictation-server',30,80,430,260,'DictationServer',['start_dictation','process_segment','stop_dictation','insert/replace edit payload'],'adapters/dictation/server.py','class')
card('dictation-store',500,80,280,260,'Session store',['UUID session ids','prune_stale()','in-memory text'],'adapters/dictation/dictation_session_store.py','class')
card('dictation-schema',820,80,280,260,'Tool schema catalog',['start / process / stop','MCP response payload'],'adapters/dictation/dictation_tool_schema_catalog.py','class')
add('<line class="micro-edge" x1="460" y1="210" x2="500" y2="210"/>')
end_dict()

# Codex process
end_codex=box('process-codex',50,2010,1150,400,'Optional Codex process','one-shot exec OR persistent mcp-server (mutually exclusive backend)','process','tusk/kernel/agent/backends/codex_exec_agent_backend.py; tusk/kernel/agent/backends/codex_mcp_agent_backend.py; docker/codex-entrypoint.sh',level=3,rx=22)
card('codex-exec-process',40,90,500,220,'codex exec',['spawn per command','structured JSON output','configured sandbox/workdir'],'tusk/kernel/agent/backends/codex_exec_agent_backend.py','class')
card('codex-mcp-process',610,90,500,220,'codex mcp-server',['single persistent subprocess','MCP tool call','thread-id conversation continuity'],'tusk/kernel/agent/backends/codex_mcp_agent_backend.py','class')
end_codex()
end_adapters()

# Host launcher
end_launcher=box('process-host-launcher',3900,2900,1250,400,'Host launcher','Unix-domain command bridge for GUI application spawning','process','launcher/tusk_host_launcher.py; adapters/gnome/tools/application_tools.py',level=2,rx=32)
card('host-launcher-server',50,100,1150,230,'tusk_host_launcher.py',['listen /tmp/tusk/launch.sock (0700)','receive command → subprocess.Popen','strip Snap-specific environment leaks'],'launcher/tusk_host_launcher.py','class')
end_launcher()

# Phoenix
end_phoenix=box('service-phoenix',3900,3400,1250,360,'Arize Phoenix','OTLP trace collector + UI','process','docker-compose.yml; tusk/shared/tracing/tracer_factory.py',level=2,rx=32)
card('phoenix-runtime',50,95,780,190,'phoenix:17.25.0',['port 6006','OTLP HTTP /v1/traces','persistent phoenix-data volume'],'docker-compose.yml','class')
card('phoenix-volume',870,95,300,190,'phoenix-data',['Docker named volume','/mnt/data'],'docker-compose.yml','datastore')
end_phoenix()

# Data stores under container
end_sessions=box('datastore-agent-sessions',250,3390,1500,360,'Agent session event store','one JSONL file per session','datastore','tusk/kernel/agent/session/file_store.py; tusk/shared/config/config_factory.py',level=2,rx=32)
card('class-file-store',40,100,700,190,'FileStore',['append_event()','conversation_messages()','session_digest()','final_result()'],'tusk/kernel/agent/session/file_store.py','class')
card('data-jsonl',790,100,660,190,'.tusk_runtime/agent_sessions/*.jsonl',['session_started','message_appended','tool steps','final result'],'tusk/kernel/agent/session/file_store.py','datastore')
end_sessions()

end_cache=box('datastore-adapter-cache',1850,3390,1800,360,'Adapter environment cache','per-adapter/version Python virtual environments','datastore','tusk/shared/mcp/adapter_env_builder.py; tusk/shared/config/config_factory.py',level=2,rx=32)
card('adapter-env-builder',40,100,800,190,'AdapterEnvironmentBuilder',['try base PYTHONPATH first','on failure: create venv','pip install adapter requirements'],'tusk/shared/mcp/adapter_env_builder.py','class')
card('adapter-cache-data',890,100,860,190,'.tusk_runtime/adapters/{name}/{version}',['bin/python','installed dependencies','PATH + VIRTUAL_ENV'],'tusk/shared/mcp/adapter_env_builder.py','datastore')
end_cache()

# Cross-boundary edges inside system (local coords)
edge('edge-shells-kernel',1300,1700,1370,1700,'submit(text, kind)','call')
edge('edge-kernel-agent',2420,1700,2490,1700,'AgentBackend.run','call')
edge('edge-agent-adapters',3640,1780,3900,1780,'ToolRegistry → MCP tools','mcp')
edge('edge-main-codex',3640,2100,3950,2470,'subprocess / MCP','mcp',curve=(3720,2100,3820,2470))
edge('edge-agent-sessions',2800,2550,1400,3390,'append/read JSONL events','data',curve=(2700,3000,1900,3200))
add('<path id="edge-adapter-cache" class="edge data low-level-edge" d="M 1930 680 C 1150 820, 180 900, 180 1750 C 180 2580, 620 3140, 1220 3290 C 1680 3400, 2320 3340, 2750 3390" marker-end="url(#arrow)"><title>Direct support: AdapterManager uses AdapterEnvironmentBuilder; on initial adapter import failure it creates a versioned venv and installs adapter requirements. Evidence: tusk/kernel/core/adapter_manager.py and tusk/shared/mcp/adapter_env_builder.py.</title></path>')
add('<text x="870" y="3190" class="edge-label low-level-label" text-anchor="middle">AdapterEnvironmentBuilder: cached venv on import failure</text>')
edge('edge-main-phoenix',3500,2950,3900,3575,'OTLP/HTTP','http',curve=(3700,3050,3800,3400))
add('<path id="edge-gnome-launcher" class="edge control" marker-end="url(#arrow)" d="M 5100 1130 C 5320 1220, 5380 1780, 5360 2350 C 5350 2690, 5230 2890, 5100 3000"><title>Direct support: GNOME ApplicationTools connects to /tmp/tusk/launch.sock; launcher/tusk_host_launcher.py accepts and executes the command.</title></path>')
add('<text x="5390" y="2070" class="edge-label" text-anchor="middle" transform="rotate(90 5390 2070)">Unix socket /tmp/tusk/launch.sock</text>')

end_system()

# External clouds
end_cloud=box('external-cloud-services',6450,480,650,1500,'Cloud model/audio APIs','network services outside the repository','external','Provider client implementations and Codex CLI configuration',level=2,rx=38)
end_groq=box('external-groq',50,140,550,430,'Groq','LLM chat + STT + TTS','provider','tusk/providers/llm/groq_llm.py; tusk/providers/stt/groq_stt.py; tusk/providers/tts/groq_tts.py',level=3,rx=24)
card('groq-apis',40,100,470,240,'Groq SDK calls',['chat.completions.create','audio.transcriptions.create','audio.speech.create'],'tusk/providers/llm/groq_llm.py; tusk/providers/stt/groq_stt.py; tusk/providers/tts/groq_tts.py','class')
end_groq()
end_or=box('external-openrouter',50,630,550,350,'OpenRouter','OpenAI-compatible LLM API','provider','tusk/providers/llm/open_router_llm.py',level=3,rx=24)
card('openrouter-api',40,100,470,190,'https://openrouter.ai/api/v1',['OpenAI client','chat.completions','tool calls'],'tusk/providers/llm/open_router_llm.py','class')
end_or()
end_openai=box('external-openai-codex',50,1040,550,350,'OpenAI model service','used by the Codex CLI runtime','external','Inferred from invoking an authenticated Codex CLI; the repository does not implement its network client.',level=3,rx=24,extra_class='inferred',badge='inferred')
card('codex-cloud-inference',40,100,470,190,'Codex upstream',['exact endpoint/protocol hidden inside binary','OAuth auth.json mounted into container'],'docker/codex-entrypoint.sh; .env.example','class',inferred=True)
end_openai()
end_cloud()

# Host GNOME environment
end_host=box('external-host-environment',6450,2140,650,1530,'Host GNOME session','desktop, sound, display, D-Bus, application files','external','docker-compose.yml; Dockerfile; adapters/gnome/*; launcher/tusk_host_launcher.py',level=2,rx=38)
end_desktop=box('external-gnome-desktop',50,130,550,480,'GNOME desktop','windows, focused editor, applications','external','adapters/gnome/gnome_context_provider.py; adapters/gnome/gnome_input_simulator.py',level=3,rx=24)
card('host-window-system',40,110,470,270,'Host commands',['wmctrl','xdotool','xclip / wl-copy','xdg-open'],'Dockerfile; adapters/gnome/','class')
end_desktop()
end_audio=box('external-audio-session',50,670,550,330,'Audio session','microphone + playback + echo cancellation','external','docker-compose.yml; docker/pipewire-echo-cancel.conf',level=3,rx=24)
card('host-audio-endpoints',40,105,470,170,'PulseAudio / PipeWire',['/dev/snd','pulse native socket','echo-cancel source/sink'],'docker-compose.yml; docker/pipewire-echo-cancel.conf','class')
end_audio()
end_display=box('external-display-bus',50,1060,550,360,'Display + desktop buses','container access to host session','external','docker-compose.yml; shells/tray/tray_shell.py',level=3,rx=24)
card('host-display-mounts',40,105,470,200,'X11 + D-Bus + .desktop dirs',['DISPLAY / XAUTHORITY','session bus socket','application directories mounted read-only'],'docker-compose.yml','class')
end_display()
end_host()

# External/top-level edges (absolute coordinates)
edge('edge-user-voice',640,1830,950,1830,'voice / CLI / tray','audio',curve=(760,1750,850,1750))
add('<path id="edge-main-groq" class="edge http" d="M 4200 3200 C 4480 3200, 4620 3200, 4620 430 C 5200 370, 6000 390, 6200 650 C 6270 760, 6360 850, 6500 900" marker-end="url(#arrow)"/>')
add('<text x="5550" y="405" class="edge-label" text-anchor="middle">HTTPS via Groq SDK</text>')
add('<path id="edge-main-openrouter" class="edge http" d="M 4300 3250 C 4540 3300, 4680 3300, 4680 465 C 5400 405, 6070 430, 6210 760 C 6280 980, 6360 1260, 6500 1420" marker-end="url(#arrow)"/>')
add('<text x="5750" y="455" class="edge-label" text-anchor="middle">HTTPS OpenAI-compatible</text>')
add('<path id="edge-coding-groq" class="edge http" d="M 5900 1820 C 6080 1800, 6200 1260, 6500 1050" marker-end="url(#arrow)"/>')
add('<text x="6240" y="1225" class="edge-label" text-anchor="middle">LLM edit planner</text>')
add('<path id="edge-codex-cloud" class="edge http inferred-edge" d="M 5900 2780 C 6100 2700, 6200 1920, 6500 1690" marker-end="url(#arrow)"/>')
add('<text x="6250" y="1905" class="edge-label" text-anchor="middle">model API (inferred)</text>')
add('<path id="edge-gnome-host" class="edge control" d="M 5900 1050 C 6100 1200, 6200 2300, 6500 2500" marker-end="url(#arrow)"/>')
add('<text x="6250" y="2315" class="edge-label" text-anchor="middle">wmctrl / xdotool / clipboard</text>')
add('<path id="edge-launcher-host" class="edge control" d="M 5900 3360 C 6100 3350, 6200 2860, 6500 2700" marker-end="url(#arrow)"/>')
add('<text x="6250" y="2865" class="edge-label" text-anchor="middle">spawn host GUI process</text>')
add('<path id="edge-container-audio" class="edge audio" d="M 4300 1900 C 4520 1900, 4640 900, 4640 400 C 5300 350, 6000 390, 6180 700 C 6240 1250, 6200 2500, 6500 3000" marker-end="url(#arrow)"/>')
add('<text x="5300" y="365" class="edge-label" text-anchor="middle">PulseAudio + /dev/snd</text>')
add('<path id="edge-container-display" class="edge control" d="M 4300 1150 C 4500 1150, 4700 760, 4700 445 C 5450 390, 6070 430, 6220 820 C 6290 1600, 6220 3000, 6500 3500" marker-end="url(#arrow)"/>')
add('<text x="5500" y="430" class="edge-label" text-anchor="middle">X11 + D-Bus mounts</text>')

# Legend
add('<g id="legend" transform="translate(120 3520)">')
add('<rect x="0" y="0" width="650" height="720" rx="30" fill="#fff" stroke="#cbd5e1" stroke-width="4"/>')
add('<text x="35" y="55" class="legend-title">Legend</text>')
legend=[('application','#edf5ff','#2563eb','Application / container'),('process','#eefcf6','#16865a','Process / service'),('module','#ffffff','#64748b','Module / component'),('provider','#fff1f1','#c24141','Provider / external API'),('datastore','#fff7db','#b7791f','Data store / persistent files')]
for i,(cls,fill,stroke,label) in enumerate(legend):
    y=90+i*58
    add(f'<rect x="35" y="{y}" width="70" height="34" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="3"/><text x="125" y="{y+24}" class="legend-text">{label}</text>')
add('<rect x="35" y="400" width="70" height="34" rx="8" fill="#faf7ff" stroke="#8b5cf6" stroke-width="3" stroke-dasharray="10 7"/><text x="125" y="424" class="legend-text">Inferred, not directly declared</text>')
add('<line x1="35" y1="474" x2="105" y2="474" stroke="#16865a" stroke-width="6" marker-end="url(#arrow)"/><text x="125" y="481" class="legend-text">MCP / JSON-RPC stdio</text>')
add('<line x1="35" y1="530" x2="105" y2="530" stroke="#c24141" stroke-width="6" marker-end="url(#arrow)"/><text x="125" y="537" class="legend-text">HTTP / external API</text>')
add('<line x1="35" y1="586" x2="105" y2="586" stroke="#b7791f" stroke-width="6" marker-end="url(#arrow)"/><text x="125" y="593" class="legend-text">Audio or persisted data</text>')
add('<text x="35" y="655" class="scope-note">Deep levels show representative implementation details.</text>')
add('<text x="35" y="680" class="scope-note">Schemas, prompts, guards, and small helpers are summarized.</text>')
add('</g>')

# Source/validation note
add('<g id="source-note" transform="translate(815 4210)">')
add('<text x="0" y="0" class="scope-note">Evidence basis: production source, adapter manifests, requirements, Docker deployment, and tests. Existing architecture docs/diagrams were ignored. Hover nodes for source paths.</text>')
add('</g>')

add('</svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text('\n'.join(parts), encoding='utf-8')
print(OUT)
print('bytes', OUT.stat().st_size)
