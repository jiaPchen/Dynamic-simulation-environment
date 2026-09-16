function ok = trucksim_config(caseStruct, caseFile, pythonExe, simfilePath)
% TRUCKSIM_CONFIG  Apply one TXT case before the TruckSim S-Function starts.
% Uses the shared, verified COM/par-file fallback from phase two. When COM is
% unavailable it updates the active simfile's parameter files with backups.

ok = false;
scriptDir = fileparts(mfilename('fullpath'));
configScript = fullfile(scriptDir, 'configure_trucksim_case.py');
if ~exist(configScript, 'file') || ~exist(pythonExe, 'file') || ...
        ~exist(simfilePath, 'file')
    warning('trucksim_config:ConfigHelperMissing', ...
        'TruckSim configuration helper, Python, or simfile is missing.');
    return;
end

% Use an ASCII temporary filename because MATLAB system() can otherwise
% garble the Chinese project path on some Windows installations.
caseCopy = [tempname '.txt'];
try
    copyfile(caseFile, caseCopy);
    oldDir = cd(scriptDir);
    cleanupDir = onCleanup(@() cd(oldDir)); %#ok<NASGU>
    cmd = sprintf('"%s" configure_trucksim_case.py --case "%s" --simfile "%s"', ...
        pythonExe, caseCopy, simfilePath);
    [st, msg] = system(cmd);
    fprintf('%s\n', msg);
    ok = st == 0 && contains(msg, 'CONFIG_READY');
catch ME
    warning('trucksim_config:ConfigHelperFailed', '%s', ME.message);
end
if exist(caseCopy, 'file')
    delete(caseCopy);
end
if ok
    fprintf('TruckSim case configuration verified: %s\n', caseStruct.case_name);
end
end
