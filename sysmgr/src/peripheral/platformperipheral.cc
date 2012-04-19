// Copyright 2012 Google Inc. All Rights Reserved.
// Author: kedong@google.com (Ke Dong)

#include "base/logging.h"
#include "base/scoped_ptr.h"
#include "base/criticalsection.h"
#include "gpioconfig.h"
#include "gpio.h"
#include "gpiofanspeed.h"
#include "platformnexus.h"
#include "ledmain.h"
#include "ledstandby.h"
#include "ledstatus.h"
#include "factoryresetbutton.h"
#include "fancontrol.h"
#include "unmute.h"
#include "flash.h"
#include "peripheralmon.h"
#include "platform_peripheral_api.h"
#include "platformperipheral.h"
#include "platform.h"
#include "ubifsmon.h"

namespace bruno_platform_peripheral {

PlatformPeripheral* PlatformPeripheral::kInstance_ = NULL;
bruno_base::CriticalSection PlatformPeripheral::kCrit_;

extern Platform* platformInstance_;

bool PlatformPeripheral::Init(unsigned int monitor_interval) {
  {
    bruno_base::CritScope lock(&kCrit_);
    if ((kInstance_ != NULL) || (platformInstance_ != NULL)) {
      LOG(LS_WARNING) << "Peripherals are already initialized...";
      return false;
    }
    LOG(LS_INFO) << "Init platformInstance_ in platformperipheral" << std::endl;
    platformInstance_ = new Platform ("Unknown Platform", BRUNO_UNKNOWN, false);
    kInstance_ = new PlatformPeripheral(platformInstance_);
  }
  /* Initialize platform */
  platformInstance_->Init();

  kInstance_->mgr_thread_ = bruno_base::Thread::Current();
  kInstance_->led_main_->Init();
  kInstance_->led_standby_->Init();
  kInstance_->led_status_->Init();
  kInstance_->factory_reset_button_->Init(kInstance_->mgr_thread_);
  kInstance_->peripheral_mon_->Init(kInstance_->mgr_thread_, monitor_interval);
  kInstance_->unmute_->Init();
  kInstance_->ubifs_mon_->Init(kInstance_->mgr_thread_, monitor_interval);
  kInstance_->flash_->Init(kInstance_->mgr_thread_,
                           kInstance_->factory_reset_button_,
                           kInstance_->ubifs_mon_);
  return true;
}

void PlatformPeripheral::Run(void) {
  kInstance_->mgr_thread_->Run();
}

bool PlatformPeripheral::Terminate(void) {
  if (kInstance_ == NULL) {
    LOG(LS_WARNING) << "Peripherals are already terminated...";
    return false;
  } else {
    kInstance_->led_main_->Terminate();
    kInstance_->led_standby_->Terminate();
    kInstance_->led_status_->Terminate();
    kInstance_->factory_reset_button_->Terminate();
    kInstance_->peripheral_mon_->Terminate();
    kInstance_->unmute_->Terminate();
    kInstance_->ubifs_mon_->Terminate();
    delete kInstance_;
    kInstance_ = NULL;
    delete platformInstance_;
    platformInstance_ = NULL;
  }
  return true;
}

void PlatformPeripheral::TurnOnLedMain(void) {
  return kInstance_->led_main_->TurnOn();
}

void PlatformPeripheral::TurnOffLedMain(void) {
  return kInstance_->led_main_->TurnOff();
}

void PlatformPeripheral::TurnOnLedStandby(void) {
  return kInstance_->led_standby_->TurnOn();
}

void PlatformPeripheral::TurnOffLedStandby(void) {
  return kInstance_->led_standby_->TurnOff();
}

bool PlatformPeripheral::SetLedStatusColor(led_status_color_e color) {
  switch (color) {
    case LED_STATUS_RED: kInstance_->led_status_->SetRed(); break;
    case LED_STATUS_ACT_BLUE: kInstance_->led_status_->SetBlue(); break;
    case LED_STATUS_PURPLE: kInstance_->led_status_->SetPurple(); break;
    default:
      return false;
  }
  return true;
}

void PlatformPeripheral::TurnOffLedStatus(void) {
  return kInstance_->led_status_->TurnOff();
}

PlatformPeripheral::PlatformPeripheral(Platform *platform)
  : led_main_(new LedMain()),
    led_standby_(new LedStandby()),
    led_status_(new LedStatus()),
    factory_reset_button_(new FactoryResetButton()),
    peripheral_mon_(new PeripheralMon(new FanControl(0, platform),
                    new GpIoFanSpeed())),
    unmute_(new Unmute()),
    ubifs_mon_(new UbifsMon(platform)),
    flash_(new Flash()) {
}

PlatformPeripheral::~PlatformPeripheral() {
}

}  // namespace bruno_platform_peripheral

#ifdef __cplusplus
extern "C" {
#endif

int platform_peripheral_init(unsigned int monitor_interval) {
  if (!bruno_platform_peripheral::PlatformPeripheral::Init(monitor_interval)) {
    return -1;
  }
  return 0;
}

void platform_peripheral_run(void) {
  bruno_platform_peripheral::PlatformPeripheral::Run();
}

int platform_peripheral_terminate(void) {
  if (!bruno_platform_peripheral::PlatformPeripheral::Terminate()) {
    return -1;
  }
  return 0;
}

void platform_peripheral_turn_on_led_main(void) {
  return bruno_platform_peripheral::PlatformPeripheral::TurnOnLedMain();
}

void platform_peripheral_turn_off_led_main(void) {
  return bruno_platform_peripheral::PlatformPeripheral::TurnOffLedMain();
}

void platform_peripheral_turn_on_led_standby(void) {
  return bruno_platform_peripheral::PlatformPeripheral::TurnOnLedStandby();
}

void platform_peripheral_turn_off_led_standby(void) {
  return bruno_platform_peripheral::PlatformPeripheral::TurnOffLedStandby();
}

int platform_peripheral_set_led_status_color(led_status_color_e color) {
  if (bruno_platform_peripheral::PlatformPeripheral::SetLedStatusColor(color)) {
    return 0;
  }
  return -1;
}

void platform_peripheral_turn_off_led_status(void) {
  return bruno_platform_peripheral::PlatformPeripheral::TurnOffLedStatus();
}

#ifdef __cplusplus
}  // extern "C" {
#endif
