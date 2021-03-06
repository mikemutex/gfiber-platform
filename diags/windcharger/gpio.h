/*
 * (C) Copyright 2015 Google, Inc.
 * All rights reserved.
 *
 */

#ifndef VENDOR_GOOGLE_DIAGS_WINDCHARGER_GPIO_H_
#define VENDOR_GOOGLE_DIAGS_WINDCHARGER_GPIO_H_

#include <inttypes.h>

#define GPIO_OE 0x18040000
#define GPIO_IN 0x18040004
#define GPIO_OUT 0x18040008
#define GPIO_SET 0x1804000C
#define GPIO_CLEAR 0x18040010
#define GPIO_OUT_FUNCTION0 0x1804002C
#define GPIO_OUT_FUNCTION1 0x18040030
#define GPIO_OUT_FUNCTION2 0x18040034
#define GPIO_OUT_FUNCTION3 0x18040038
#define GPIO_OUT_FUNCTION4 0x1804003C
#define RST_RESET 0x1806001C

#define GPIO_BLUE_LED_PIN 11
#define GPIO_POE_PIN 12
#define GPIO_DIM_LED_PIN 15
#define GPIO_RED_LED_PIN 16
#define MAX_GPIO_PIN_NUM 17

#define GPIO_CPU_CNTL_VAL 0
#define GPIO_SYS_RST_L_VAL 1
#define GPIO_CPU_CNTL_MAX_VAL 127
#define GPIO_CNTL_PER_REG 4
#define GPIO_RESET_BUTTON_PIN 13

#define CPU_COLD_RESET_BIT 20

#endif  // VENDOR_GOOGLE_DIAGS_WINDCHARGER_GPIO_H_
