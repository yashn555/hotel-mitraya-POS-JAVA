package com.hotelmitraya.pos.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class ApiResponse<T> {

    @SerializedName("success")
    private boolean success;

    @SerializedName("message")
    private String message;

    @SerializedName("error")
    private String error;

    @SerializedName("role")
    private String role;

    @SerializedName("name")
    private String name;

    @SerializedName("user_id")
    private Long userId;

    @SerializedName("redirect")
    private String redirect;

    @SerializedName("tables")
    private List<DiningTableModel> tables;

    @SerializedName("categories")
    private List<CategoryModel> categories;

    @SerializedName("bills")
    private List<PosBillModel> bills;

    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public String getError() { return error; }
    public void setError(String error) { this.error = error; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }

    public String getRedirect() { return redirect; }
    public void setRedirect(String redirect) { this.redirect = redirect; }

    public List<DiningTableModel> getTables() { return tables; }
    public void setTables(List<DiningTableModel> tables) { this.tables = tables; }

    public List<CategoryModel> getCategories() { return categories; }
    public void setCategories(List<CategoryModel> categories) { this.categories = categories; }

    public List<PosBillModel> getBills() { return bills; }
    public void setBills(List<PosBillModel> bills) { this.bills = bills; }
}
