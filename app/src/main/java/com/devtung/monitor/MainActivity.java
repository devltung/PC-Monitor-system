package com.devtung.monitor;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.Toast;
import android.os.Build;

public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        
        Button btnStart = new Button(this);
        btnStart.setText("BẬT HỆ THỐNG THEO DÕI NGẦM");
        
        btnStart.setOnClickListener(v -> {
            Intent serviceIntent = new Intent(this, MonitorService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }
            Toast.makeText(this, "Đã kích hoạt chạy ngầm vĩnh viễn!", Toast.LENGTH_SHORT).show();
            finish(); 
        });

        layout.addView(btnStart);
        setContentView(layout);
    }
}
