/* ========================================
 *
 * Copyright YOUR COMPANY, THE YEAR
 * All Rights Reserved
 * UNPUBLISHED, LICENSED SOFTWARE.
 *
 * CONFIDENTIAL AND PROPRIETARY INFORMATION
 * WHICH IS THE PROPERTY OF your company.
 *
 * ========================================
*/
#include "project.h"


/*****************************************************************************\
 * Function:    genericEventHandler(uint32_t event, void *eventParameter)
 * Input:       uint32_t event, void *eventParameter
 * Returns:     void
 * Description: 
 *   This function handles the BLE events. It powers the green LED when the BLE
 *   connection is active. It starts a BLE advertisement when disconnected.
 *   It handles the GREEN_LED_INV write and the RED_LED_INV write requests.
\*****************************************************************************/
void genericEventHandler(uint32_t event, void *eventParameter)
{
    cy_stc_ble_gatts_write_cmd_req_param_t   *writeReqParameter;
    
    /* Take an action based on the current event */
    switch (event)
    {
      
        /* This event is received when the BLE stack is Started */
        case CY_BLE_EVT_STACK_ON:
        case CY_BLE_EVT_GAP_DEVICE_DISCONNECTED:
            Cy_GPIO_Set(LED_GREEN_PORT, LED_GREEN_NUM); //Turn off the LED_GREEN when disconnected
            Cy_BLE_GAPP_StartAdvertisement(CY_BLE_ADVERTISING_FAST, CY_BLE_PERIPHERAL_CONFIGURATION_0_INDEX);
        break;

        case CY_BLE_EVT_GATT_CONNECT_IND: // Connection indication
            Cy_GPIO_Clr(LED_GREEN_PORT, LED_GREEN_NUM); //Turn on the LED_GREEN when connected
        break;
        
        case CY_BLE_EVT_GATTS_WRITE_REQ: // When the other side sends the write request
            writeReqParameter = (cy_stc_ble_gatts_write_cmd_req_param_t *)eventParameter;
            
            /* Toggles the green LED when the value "true" is sent through the BLE GREEN_LED_TOGGLE characteristic.*/
            if (CY_BLE_DEVICE_INTERFACE_GREEN_LED_TOGGLE_CHAR_HANDLE == writeReqParameter->handleValPair.attrHandle) {              
                bool toggle = writeReqParameter->handleValPair.value.val[0];
                if (toggle) {
                    Cy_GPIO_Inv(LED_GREEN_PORT, LED_GREEN_NUM);
                    toggle = false;
                }
            }
            
            /* Toggles the red LED when the value "true" is sent through the BLE RED_LED_TOGGLE characteristic.*/
            if (CY_BLE_DEVICE_INTERFACE_RED_LED_TOGGLE_CHAR_HANDLE == writeReqParameter->handleValPair.attrHandle) {              
                bool toggle = writeReqParameter->handleValPair.value.val[0];
                if (toggle) {
                    Cy_GPIO_Inv(LED_RED_PORT, LED_RED_NUM);
                    toggle = false;
                }
            }
                     
            Cy_BLE_GATTS_WriteRsp(writeReqParameter->connHandle);
            break;
        
        default:
            break;
    }
}

/*****************************************************************************\
 * Function:    bleInterruptNotify
 * Input:       void (it is called inside of the ISR)
 * Returns:     void
 * Description: 
 *   This is called back in the BLE ISR when an event has occured and needs to
 *   be processed.
\*****************************************************************************/
void bleInterruptNotify()
{
    Cy_BLE_ProcessEvents();
}

int main(void)
{
    __enable_irq(); /* Enable global interrupts. */
    
    Cy_BLE_Start(0);
    /* Enable CM4.  CY_CORTEX_M4_APPL_ADDR must be updated if CM4 memory layout is changed. */
    Cy_SysEnableCM4(CY_CORTEX_M4_APPL_ADDR); 

    Cy_BLE_Start(genericEventHandler);
    
    Cy_BLE_RegisterAppHostCallback(bleInterruptNotify);

    for(;;)
    {
        /* Place your application code here. */
    }
}

/* Code references:
 *      BLE communication: https://www.youtube.com/watch?v=Aeip0hkc4YE
*/

/* [] END OF FILE */
