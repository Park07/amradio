AM Radio break-in System

Both the software and hardware is integrated to generate up to 12 channels simultaneously*.

- GUI: Uses DearPyGui and Observer Pattern to loosely reference the components. It's easier to add or edit other components without spaghettigied code.
- 'Network Manager'. Polls every 5 seconds to check the status of the device, it will gather all the network requests and send the command over to the Red Pitaya (RP) via TCP/SCPI. THis is important to ensure that both the software and hardware are in sync with each other. After 5 re-tries, it will terminate the program
- Stateless UI: Have achieved a true stateless whereby the GUI won't update the display until it has confirmed the device is active.
- The Red Pitaya has NCO which generates the carrier frequencies, and our code AM modulates it. The RF Output it generates are the wavebands that you see where the message has been combined with the carrier frequency.
- Fail-safe watchdog has not yet been implemented and is WIP.

Other than the watchdog, we have tested this both on SDR and actual radio, and the functionalities work as intended.


* Note that at 12 channels, because the Red Pitaya outputs a fixed power, the amplitudes get much lower. The max that I recommend is 4 - 5 and after that it falls off.

[updated 30th January by William Park]