function tcp_client_sfun(block)
% TCP_CLIENT_SFUN  Simulink <-> Python TCP 客户端（Level-2 M S-Function，阶段二）
%   输入(3)：[Vx_kmh, beta_deg, w_degps]  （TruckSim 输出状态）
%   输出(6)：[d1L,d1R,d2L,d2R,d3L,d3R]    （各轴转角指令，deg，直接进 TruckSim 输入）
%   协议：JSON 行（UTF-8），HELLO/READY/STATE/CONTROL/STOP，与 tcp_server.py 对应。
%   注意：必须先用 tcp_server.py 启动服务并处于 LISTENING 状态，模型才能初始化。
%   连接对象用 persistent 容器保存（Dwork 只能存数值，不能存结构体/Java 对象）。

setup(block);
end

function setup(block)
block.NumInputPorts  = 1;
block.NumOutputPorts = 1;

block.SetPreCompInpPortInfoToDynamic;
block.SetPreCompOutPortInfoToDynamic;

block.InputPort(1).Dimensions        = 3;   % [Vx_kmh, beta_deg, w_degps]
block.InputPort(1).DirectFeedthrough = true;
block.InputPort(1).SamplingMode      = 'Sample';

block.OutputPort(1).Dimensions       = 6;   % [d1L,d1R,d2L,d2R,d3L,d3R]
block.OutputPort(1).SamplingMode     = 'Sample';

% 控制周期 0.01 s（与阶段二数据采集周期一致）
block.SampleTimes = [0.01 0];
block.SimStateCompliance = 'DefaultSimState';

block.RegBlockMethod('Start',     @Start);
block.RegBlockMethod('Outputs',   @Outputs);
block.RegBlockMethod('Terminate', @Terminate);
end

function Start(block)
% 建立 TCP 连接并完成 HELLO/READY 握手
host = '127.0.0.1';
try
    port = evalin('base', 'tcp_port');
    if isempty(port) || ~isnumeric(port) || port <= 0
        port = 50007;
    end
catch
    port = 50007;   % 未设置时默认 50007
end
dt = 0.01;
interfaceVersion = 'p2-tcp-v1';

d = struct();
d.socket = java.net.Socket(host, port);
d.socket.setSoTimeout(2000);
d.out = java.io.PrintWriter( ...
    java.io.BufferedWriter( ...
    java.io.OutputStreamWriter(d.socket.getOutputStream(), 'UTF-8')), true);
d.inp = java.io.BufferedReader( ...
    java.io.InputStreamReader(d.socket.getInputStream(), 'UTF-8'));
d.step = 0;

hello = struct('type','HELLO','protocol',1,'dt',dt, ...
    'interface_version', interfaceVersion, ...
    'units', struct('Vx_kmh','km/h','beta_deg','deg','w_degps','deg/s', ...
                    'controls','deg'), ...
    'inputs', {{'Vx_kmh','beta_deg','w_degps'}}, ...
    'outputs', {{'d1L','d1R','d2L','d2R','d3L','d3R'}});
d.out.println(jsonencode(hello));

line = char(d.inp.readLine());   % readLine() 返回 Java String，转成 MATLAB 字符向量
if isempty(line)
    error('tcp:handshake', 'Python 服务未返回 READY（请先启动 tcp_server.py）');
end
resp = jsondecode(line);
if ~isfield(resp, 'type') || ~strcmp(resp.type, 'READY')
    error('tcp:handshake', '握手失败: %s', line);
end
if ~isfield(resp, 'dt') || abs(double(resp.dt) - dt) > 1e-12 || ...
        ~isfield(resp, 'interface_version') || ...
        ~strcmp(resp.interface_version, interfaceVersion)
    error('tcp:handshake', 'READY 的周期或接口版本不一致: %s', line);
end

conn_store(block, 'set', d);
end

function Outputs(block)
d  = conn_store(block, 'get');
t  = block.CurrentTime;
st = block.InputPort(1).Data(:)';
% 通信失败时先写入安全零转角，再终止仿真，避免保留上一拍控制量。
block.OutputPort(1).Data = zeros(1, 6);

msg = struct('type','STATE','step_id',d.step,'t',t,'states',st);
try
    d.out.println(jsonencode(msg));
    line = char(d.inp.readLine());   % Java String -> MATLAB char
catch ME
    error('tcp:comm', 'TCP 通信异常(超时/断开): %s', ME.message);
end
if isempty(line)
    error('tcp:disconnect', 'Python 服务连接已关闭');
end

resp = jsondecode(line);
if ~isfield(resp, 'type') || ~strcmp(resp.type, 'CONTROL') || resp.step_id ~= d.step
    error('tcp:badresp', '收到异常或乱序响应: %s', line);
end

ctrl = double(resp.controls(:)');
if numel(ctrl) ~= 6 || any(~isfinite(ctrl))
    error('tcp:dim', '控制量维度错误(应为6): %d', numel(ctrl));
end
block.OutputPort(1).Data = ctrl;

d.step = d.step + 1;
conn_store(block, 'set', d);
end

function Terminate(block)
d = conn_store(block, 'get');
if ~isempty(fieldnames(d))
    try
        d.out.println(jsonencode(struct('type','STOP')));
    catch
    end
    try d.out.close(); catch; end
    try d.inp.close(); catch; end
    try d.socket.close(); catch; end
end
conn_store(block, 'clear');
end

function d = conn_store(block, action, data)
% 用 persistent 容器按 block 句柄保存 TCP 连接对象（Dwork 不能存结构体/对象）
persistent store
if isempty(store)
    store = containers.Map('KeyType','double','ValueType','any');
end
key = block.BlockHandle;
switch action
    case 'set'
        store(key) = data;
        d = [];
    case 'get'
        if isKey(store, key)
            d = store(key);
        else
            d = struct();
        end
    case 'clear'
        if isKey(store, key)
            remove(store, key);
        end
        d = [];
    otherwise
        d = [];
end
end
