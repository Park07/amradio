clc; clear; close all;

%% ===== Parameters =====
wavFile = "MXLamAMF.wav";   % Upload file
fc      = 750e3;              % carrier wave frequency 750 kHz
m       = 1;                % Modulation Index 0~1
fs_rf   = 5e6;               % RF sampling frequency
show_ms = 50;                  % Duration (ms)

%% =====  Read in original waveform (baseband)=====
[x, fs_audio] = audioread(wavFile);
if size(x,2) > 1, x = mean(x,2); end
x = x - mean(x);
x = x / (max(abs(x)) + 1e-12);

fprintf("Audio sampling rate = %.0f Hz\n", fs_audio);

% Take one period (s)

use_s = min(4, length(x)/fs_audio);
x = x(1:floor(use_s*fs_audio));

%% =====  Resampling to RF sampling rate =====

x_rf = resample(x, fs_rf, fs_audio);
x_rf = x_rf / (max(abs(x_rf)) + 1e-12);   % Normalization
t = (0:length(x_rf)-1).'/ fs_rf;

%% =====  Add carrier wave & AM Modulation =====

Ac = 1;  % Amplitude of the carrier wave
carrier = Ac * cos(2*pi*fc*t);
am      = Ac * m*x_rf .* cos(2*pi*fc*t);

%% ===== Comparing on the same time line =====

Ns = min(round(show_ms*1e-3*fs_rf), length(t));
ts = t(1:Ns);

x_show = x_rf(1:Ns);
c_show = carrier(1:Ns);
am_show = am(1:Ns);

figure('Color','w','Name','Waveform Comparison');

subplot(3,1,1);
plot(ts*1e3, x_show, 'LineWidth', 1);
grid on;
xlabel('Time (ms)'); ylabel('Amplitude');
title('Original waveform (baseband, normalized)');

subplot(3,1,2);
plot(ts*1e3, c_show, 'LineWidth', 1);
grid on;
xlabel('Time (ms)'); ylabel('Amplitude');
title(sprintf('Carrier (%.0f kHz)', fc/1e3));
ylim([-1.5 1.5]);

subplot(3,1,3);
plot(ts*1e3, am_show, 'LineWidth', 1);
grid on;
xlabel('Time (ms)'); ylabel('Amplitude');
title(sprintf('AM modulated signal (m = %.2f, fc = %.0f kHz)', m, fc/1e3));

%% ===== Save AM waveform to WAV file =====

%am_out = am / (max(abs(am)) + 1e-12);

% Save as 16-bit PCM WAV
%outFile = "AM.wav";
%audiowrite(outFile, am_out, fs_rf, "BitsPerSample", 16);

%fprintf("AM waveform saved to %s\n", outFile);
%fprintf("Duration: %.2f s, Sampling rate: %.0f Hz\n", length(am_out)/fs_rf, fs_rf);
