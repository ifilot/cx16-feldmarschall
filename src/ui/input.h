#ifndef _INPUT_H
#define _INPUT_H

/* One shared pointer for mouse and SNES controllers; keyboard menu navigation
 * wins simultaneous events. The keyboard joystick (port 0) is not polled. */
void input_read(void);

#endif
