uniform sampler2D u_bend;
in vec2 in_pos;
in vec4 i_pos;    // xyz, taille
in vec4 i_col;    // rgb HDR, alpha
in vec4 i_vel;    // direction d'etirement xyz, type
out vec2 v_uv; out vec4 v_col; flat out int v_kind;
void main(){
    v_uv = in_pos; v_col = i_col; v_kind = int(i_vel.w+.5);
    vec3 c = i_pos.xyz;
    vec2 b = texture(u_bend, vec2((c.z + 30.) / u_track.z, .5)).xy;
    vec3 st = i_vel.xyz; float l = length(st);
    vec3 p;
    if(l > .001){
        vec3 ax = st / l, tv = normalize(u_cam.xyz - c);
        vec3 sd = normalize(cross(ax, tv));
        p = c + ax*in_pos.y*(l*.5 + i_pos.w) + sd*in_pos.x*i_pos.w;
    } else p = c + (u_right.xyz*in_pos.x + u_up.xyz*in_pos.y)*i_pos.w;
    p.xy += b;
    gl_Position = u_vp * vec4(p, 1.);
}