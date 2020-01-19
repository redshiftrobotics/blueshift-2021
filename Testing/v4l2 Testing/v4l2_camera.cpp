/* Code modified from: https://github.com/raspberrypi/linux/issues/1297 */
/* Run:
 *    c++ -O3 -Wall -shared -std=c++11 -fPIC `python3 -m pybind11 --includes` v4l2_camera.cpp -o v4l2_camera`python3-config --extension-suffix`
 * to compile this program as a python library
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <stdbool.h>
#include <sys/time.h>
#include <unistd.h>
#include <termios.h>
#include <iostream>

#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <errno.h>
#include <time.h>

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
namespace py = pybind11;

#define CLEAR(x) memset(&(x), 0, sizeof(x))

using namespace std;
class Camera {
    private:
        char* un_fourcc(uint32_t fcc);
        void close_camera(int fd);
        int open_device(int* camfd);
        int setup_device(int fd);
        int dq_buffer(int fd, struct v4l2_buffer *buf, int *index, size_t *size);    
        int q_buffer(int fd, struct v4l2_buffer *buf);
        int init_camera(int* camera_fd);

        void **image_buf;
        size_t image_size = 0;
        int w = 0;
        int h = 0;
        const char* devname;
        char *p;
        char c;
        int fd, rv;
        void *data;
        size_t size;
        clock_t clock_s, clock_e;
        struct timeval tvs, tve;
        int frame_count = 0;
        int index;
        size_t len;
        int QUEUE_NUM = 4;

    public:
        Camera(const std::string& device = "/dev/video0",
               int width = 1920,
               int height = 1080,
               int q_num = 4);
        
        ~Camera();
        py::array_t<int8_t> get_frame();
};

Camera::Camera(const std::string& device, int width, int height, int q_num) {
    devname = device.c_str();
    w = width;
    h = height;
    QUEUE_NUM = q_num;
    rv = init_camera(&fd);
    /*
    if (rv) {
        printf("\n init camera failure, exit\n");
        // throw error
    } else printf("init camera ok\n");
    */
}

Camera::~Camera() {
    close_camera(fd);
}

py::array_t<int8_t> Camera::get_frame() {
    struct v4l2_buffer buf;

    CLEAR(buf);
    rv = dq_buffer(fd, &buf, &index, &len);
    if (rv) {
        printf("\n dqbuf nok\n");
        // throw error
    }

    int8_t* img_array = (int8_t *) image_buf[index];
    py::array_t<int8_t> img = py::array_t<int8_t>(len);

    //cout << "len: " << len << endl;

    
    auto img_data = img.mutable_data();
    /*
    for (int i=0; i<len-1; i++) {
        img_data[i] = *(img_array + i);
    }
    */

    memcpy(img_data, img_array, len);

    rv = q_buffer(fd, &buf);
    if (rv) {
        printf("\n qbuf nok\n");
        // throw error
    }

    frame_count++;
    return img;
}

char* Camera::un_fourcc(uint32_t fcc)
{
    static char s[5];

    s[0] = fcc & 0xFF;
    s[1] = (fcc >> 8) & 0xFF;
    s[2] = (fcc >> 16) & 0xFF;
    s[3] = (fcc >> 24) & 0xFF;
    s[4] = '\0';

    return s;
}

int Camera::open_device(int *camfd)
{
    struct v4l2_capability cap;
    struct v4l2_format format;

    //devname = (char*) "/dev/video0";
    //fd = open(devname, O_RDWR | O_NONBLOCK);
    fd = open(devname, O_RDWR);
    if (fd == -1) {
        printf("open camera %s", strerror(errno));
        return 1;
    }

    CLEAR(cap);
    if (ioctl(fd, VIDIOC_QUERYCAP, &cap) == -1) {
        printf("ioctl QUERYCAP %s", strerror(errno));
        return 1;
    }

    if (!(cap.capabilities & V4L2_CAP_VIDEO_CAPTURE)) {
        printf("camera don't support Video Capture");
        return 1;
    }

    if (!(cap.capabilities & V4L2_CAP_STREAMING)) {
        printf("camera don't support the stream i/o method");
        return 1;
    }

    CLEAR(format);
    format.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(fd, VIDIOC_G_FMT, &format) == -1) {
        printf("ioctl G_FMT %s", strerror(errno));
        return 1;
    }

    //format.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV;
    //format.fmt.pix.pixelformat = V4L2_PIX_FMT_YUV420;
    //format.fmt.pix.pixelformat = V4L2_PIX_FMT_MJPEG;
    format.fmt.pix.pixelformat = V4L2_PIX_FMT_H264;
    format.fmt.pix.width = w;
    format.fmt.pix.height = h;
    if (ioctl(fd, VIDIOC_S_FMT, &format) == -1) {
        printf("ioctl S_FMT %s", strerror(errno));
        return 1;
    }

    /*
     * done
     */
    //printf("camera driver name %s\n", cap.driver);
    //printf("camera name %s\n", cap.card);
    //printf("camera bus %s\n", cap.bus_info);
    //printf("camera default %zd %zd format: %s size: %zd\n",
    //       format.fmt.pix.width, format.fmt.pix.height,
    //       un_fourcc(format.fmt.pix.pixelformat), format.fmt.pix.sizeimage);

    *camfd = fd;
    image_size = format.fmt.pix.sizeimage;
    //image_width = format.fmt.pix.width;
    //image_height = format.fmt.pix.height;

    return 0;
}

int Camera::setup_device(int fd)
{
    struct v4l2_requestbuffers reqbuf;
    CLEAR(reqbuf);
    reqbuf.count = QUEUE_NUM;
    reqbuf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    reqbuf.memory = V4L2_MEMORY_USERPTR;
    if (ioctl(fd, VIDIOC_REQBUFS, &reqbuf) == -1) {
        printf("camera don't support user point i/o");
        return 1;
    }

    image_buf = (void**) calloc(QUEUE_NUM, sizeof(void*));
    for (int i = 0; i < QUEUE_NUM; i++) {
        image_buf[i] = malloc(image_size);
    }

    for (int i = 0; i < QUEUE_NUM; i++) {
        struct v4l2_buffer buf;

        CLEAR(buf);
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_USERPTR;
        buf.index = i;
        buf.m.userptr = (unsigned long)image_buf[i];
        buf.length = image_size;
        if (ioctl(fd, VIDIOC_QBUF, &buf) == -1) {
            printf("device on ioctl QBUF %s", strerror(errno));
            return 1;
        }
    }

    enum v4l2_buf_type type;
    type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(fd, VIDIOC_STREAMON, &type) == -1) {
        printf("ioctl STREAMON %s", strerror(errno));
        return 1;
    }

    return 0;
}

int Camera::dq_buffer(int fd, struct v4l2_buffer *buf, int *index, size_t *size)
{
    buf->type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf->memory = V4L2_MEMORY_USERPTR;
    if (ioctl(fd, VIDIOC_DQBUF, buf) == -1) {
        printf("ioctl DQBUF %s", strerror(errno));
        return 1;
    }

    *index = buf->index;
    *size = buf->bytesused;

    //printf("buf %d filled\n", i);

    return 0;
}

int Camera::q_buffer(int fd, struct v4l2_buffer *buf)
{
    if (ioctl(fd, VIDIOC_QBUF, buf) == -1) {
        printf("ioctl QBUF %s", strerror(errno));
        return 1;
    }

    return 0;
}

int Camera::init_camera(int *camera_fd)
{
    fd = 0;

    rv = open_device(&fd);
    if (rv) return rv;

    rv = setup_device(fd);
    if (rv) return rv;

    *camera_fd = fd;

    return 0;
}

void Camera::close_camera(int fd)
{
    enum v4l2_buf_type type;

    type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    ioctl(fd, VIDIOC_STREAMOFF, &type);
    for (int i = 0; i < QUEUE_NUM; i++) free(image_buf[i]);
    free(image_buf);
    close(fd);
}

PYBIND11_MODULE(v4l2_camera,m)
{
    m.doc() = "Python bindings for v4l2 (Video for Linux 2)";

    py::class_<Camera>(m,"Camera")
        .def( py::init( []( std::string path, int width, int height, int q_num)
            {
                return new Camera(path, width, height, q_num);
            }
            )
        )
    .def( "get_frame", &Camera::get_frame, "A function to retrieve a frame of video from the camera");
}


/* Working Program:

 * Create v4l2_requestbuffers test REQBUFS
 * m_image_buf = calloc(4, sizeof(void*)) each: malloc(fmt.fmt.pix.sizeimage)
 * Each:
   * clear v4l2_buffer
   * QBUF
 * v4l2_buf_type STREAMON
 * forever
   * Create v4l2_buffer + clear
   * DQBUF
   * use image
   * QBUF
 * STREAMOFF
 * m_image_buf each: free
 * free m_image_buf
*/

/* Broken Program:
 * Create v4l2_capability test QUERYCAP
 * Create v4l2_cropcap
 * Create v4l2_crop
 * Create v4l2_format run G_FMT
 * Create v4l2_requestbuffers test REQBUFS
 * m_image_buf calloc(4, sizeof(void*)) each: malloc(fmt.fmt.pix.sizeimage)
 * Each:
   * clear v4l2_buffer
   * QBUF
 * v4l2_buf_type STREAMON
 * Each get_frame():
   * Create v4l2_buffer + clear
   * DQBUF
   * use image
   * QBUF
 * STREAMOFF
 * m_image_buf each: free
 * free m_image_buf
*/
