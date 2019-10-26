#include <iostream>
#include <fstream>

#include "webcam.h"

#define XRES 1920
#define YRES 1080

using namespace std;

int main(int argc, char** argv)
{

    Webcam webcam("/dev/video0", XRES, YRES);
    unsigned char frame = webcam.frame();

    //int * img = (int *) frame;
    //cout << img+16 << endl;
    //cout << img << endl;
    cout << frame << endl;

    /*
    ofstream image;
    image.open("frame.ppm");
    image << "P6\n" << XRES << " " << YRES << " 255\n";
    image.write((char *) frame.data, frame.size);
    image.close();
    */

    return 0;

}
