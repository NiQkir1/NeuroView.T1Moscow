'use client'

import { useNotifications } from '../hooks/useNotifications'
import Notification from './Notification'

export default function NotificationContainer() {
  const { notifications, removeNotification } = useNotifications()

  return (
    <div className="fixed top-20 right-6 z-[60] flex flex-col gap-3 max-w-md w-full pointer-events-none">
      <div className="flex flex-col gap-3 pointer-events-auto">
        {notifications.map((notification) => (
          <Notification
            key={notification.id}
            notification={notification}
            onClose={removeNotification}
          />
        ))}
      </div>
    </div>
  )
}

