/*
Modified version of https://github.com/bitcraze/aideck-gap8-examples/tree/9bb9b1c157645e877db9677bc35f383c6dc667dd/GAP8/test_functionalities/wifi_jpeg_streamer

Used a simple state machine to send image data if it receives a picture command over UART. Lines 43-75 is where all the work is being done
*/

#include "bsp/camera/himax.h"
#include "bsp/camera/mt9v034.h"
#include "bsp/transport/nina_w10.h"
#include "tools/frame_streamer.h"
#include "stdio.h"

#if defined(CONFIG_GAPUINO) || defined(CONFIG_AI_DECK)
#define CAM_WIDTH    324
#define CAM_HEIGHT   244
#else
#define CAM_WIDTH    320
#define CAM_HEIGHT   240
#endif

#define PICTURE_COMMAND 'c'

static pi_task_t task1;
static pi_task_t task2;
static unsigned char *imgBuff0;
static unsigned char *imgBuff1;
static struct pi_device camera;
static struct pi_device wifi;
static frame_streamer_t *streamer1;
static frame_streamer_t *streamer2;
static pi_buffer_t buffer;
static pi_buffer_t buffer2;
static volatile int stream_done;

//uart
static PI_L2 uint32_t uart_value;
struct pi_uart_conf uart_conf;
struct pi_device uart_device;

static void streamer_handler(void *arg);

// State machine has three handler states: camera handler, uart handler, and streamer handler. See states.jpg for a visual

static void cam_handler(void *arg){ 
  printf("Called function is: %s\n",__func__);
  pi_camera_control(&camera, PI_CAMERA_CMD_STOP, 0); //Stop image capture

  frame_streamer_send_async(streamer1, &buffer, pi_task_callback(&task1, streamer_handler, (void *)&stream_done)); //Send image to frame buffer, which is then sent to the ESP32

  stream_done = 0;

  return;
}

static void uart_handler(void *arg){
  printf("Called function is: %s\n",__func__);
  if(uart_value){
    printf("UART value: %c\n", uart_value);
  }
  if(uart_value == PICTURE_COMMAND){ //if picture command, take picture and go to cam service
    printf("Going to take a photo\n");
    pi_camera_control(&camera, PI_CAMERA_CMD_START, 0); //Start the camera
    pi_camera_capture_async(&camera, imgBuff0, CAM_WIDTH*CAM_HEIGHT, pi_task_callback(&task1, cam_handler, NULL)); //Take the photo and go to cam handler
  }
  else{ //otherwise circle back for picture command
    printf("No photo\n");
    pi_uart_read_async(&uart_device, &uart_value, 1, pi_task_callback(&task1, uart_handler, NULL)); //Go back to uart handler in case of bad UART cmd
  }
}

static void streamer_handler(void *arg){
  printf("Called function is: %s\n",__func__);
  stream_done = 1;
  while (!stream_done); //wait for picture to stop streaming
  pi_uart_read_async(&uart_device, &uart_value, 1, pi_task_callback(&task1, uart_handler, NULL)); //Read uart and go to handler
}



static int open_pi_camera_himax(struct pi_device *device)
{
  struct pi_himax_conf cam_conf;

  pi_himax_conf_init(&cam_conf);

  cam_conf.format = PI_CAMERA_QVGA;

  pi_open_from_conf(device, &cam_conf);
  if (pi_camera_open(device))
    return -1;


    // rotate image
  pi_camera_control(&camera, PI_CAMERA_CMD_START, 0);
  uint8_t set_value=3;
  uint8_t reg_value;
  pi_camera_reg_set(&camera, IMG_ORIENTATION, &set_value);
  pi_time_wait_us(1000000);
  pi_camera_reg_get(&camera, IMG_ORIENTATION, &reg_value);
  if (set_value!=reg_value)
  {
    printf("Failed to rotate camera image\n");
    return -1;
  }
  pi_camera_control(&camera, PI_CAMERA_CMD_STOP, 0);
  
  pi_camera_control(device, PI_CAMERA_CMD_AEG_INIT, 0);

  return 0;
}



static int open_pi_camera_mt9v034(struct pi_device *device)
{
  struct pi_mt9v034_conf cam_conf;

  pi_mt9v034_conf_init(&cam_conf);

  cam_conf.format = PI_CAMERA_QVGA;

  pi_open_from_conf(device, &cam_conf);
  if (pi_camera_open(device))
    return -1;


  
  return 0;
}



static int open_camera(struct pi_device *device)
{
#ifdef CONFIG_GAPOC_A
  return open_pi_camera_mt9v034(device);
#endif
#if defined(CONFIG_GAPUINO) || defined(CONFIG_AI_DECK)
  return open_pi_camera_himax(device);
#endif
  return -1;
}


static int open_wifi(struct pi_device *device)
{
  struct pi_nina_w10_conf nina_conf;

  pi_nina_w10_conf_init(&nina_conf);

  nina_conf.ssid = "";
  nina_conf.passwd = "";
  nina_conf.ip_addr = "0.0.0.0";
  nina_conf.port = 5555;
  pi_open_from_conf(device, &nina_conf);
  if (pi_transport_open(device))
    return -1;

  return 0;
}


static frame_streamer_t *open_streamer(char *name)
{
  struct frame_streamer_conf frame_streamer_conf;

  frame_streamer_conf_init(&frame_streamer_conf);

  frame_streamer_conf.transport = &wifi;
  frame_streamer_conf.format = FRAME_STREAMER_FORMAT_JPEG;
  frame_streamer_conf.width = CAM_WIDTH;
  frame_streamer_conf.height = CAM_HEIGHT;
  frame_streamer_conf.depth = 1;
  frame_streamer_conf.name = name;

  return frame_streamer_open(&frame_streamer_conf);
}
static pi_task_t led_task;
static int led_val = 0;
static struct pi_device gpio_device;
static void led_handle(void *arg)
{
  pi_gpio_pin_write(&gpio_device, 2, led_val);
  led_val ^= 1;
  pi_task_push_delayed_us(pi_task_callback(&led_task, led_handle, NULL), 500000);
}

int main()
{
  printf("Entering main controller...\n");

  pi_freq_set(PI_FREQ_DOMAIN_FC, 150000000);

  // Open uart
  pi_uart_conf_init(&uart_conf);
  uart_conf.baudrate_bps =115200;
  pi_open_from_conf(&uart_device, &uart_conf);
  printf("[UART] Open\n");
  if (pi_uart_open(&uart_device))
  {
    printf("[UART] open failed !\n");
    pmsis_exit(-1);
  }

  pi_uart_open(&uart_device);

  pi_gpio_pin_configure(&gpio_device, 2, PI_GPIO_OUTPUT);

  pi_task_push_delayed_us(pi_task_callback(&led_task, led_handle, NULL), 500000);

  imgBuff0 = (unsigned char *)pmsis_l2_malloc((CAM_WIDTH*CAM_HEIGHT)*sizeof(unsigned char));
  if (imgBuff0 == NULL) {
      printf("Failed to allocate Memory for Image \n");
      return 1;
  }
  printf("Allocated Memory for Image\n");

  if (open_camera(&camera))
  {
    printf("Failed to open camera\n");
    return -1;
  }
  printf("Opened Camera\n");



  if (open_wifi(&wifi))
  {
    printf("Failed to open wifi\n");
    return -1;
  }
  printf("Opened WIFI\n");



  streamer1 = open_streamer("camera");
  if (streamer1 == NULL)
    return -1;

  printf("Opened streamer\n");

  pi_buffer_init(&buffer, PI_BUFFER_TYPE_L2, imgBuff0);
  pi_buffer_set_format(&buffer, CAM_WIDTH, CAM_HEIGHT, 1, PI_BUFFER_FORMAT_GRAY);

  pi_camera_control(&camera, PI_CAMERA_CMD_STOP, 0);
  pi_camera_capture_async(&camera, imgBuff0, CAM_WIDTH*CAM_HEIGHT, pi_task_callback(&task1, cam_handler, NULL));
  pi_camera_control(&camera, PI_CAMERA_CMD_START, 0);

  while(1)
  {
    pi_yield();
  }

  return 0;
}
