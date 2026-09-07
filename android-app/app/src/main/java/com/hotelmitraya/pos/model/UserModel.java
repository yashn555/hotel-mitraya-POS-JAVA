package com.hotelmitraya.pos.model;

import com.google.gson.annotations.SerializedName;

public class UserModel {

    @SerializedName("id")
    private Long id;

    @SerializedName("username")
    private String username;

    @SerializedName("role")
    private String role;

    @SerializedName("name")
    private String name;

    public Long getId() { return id; }
    public String getUsername() { return username; }
    public String getRole() { return role; }
    public String getName() { return name; }
}
