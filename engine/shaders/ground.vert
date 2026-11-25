uniform sampler2D u_bend;
uniform int u_part;             // 0 route, 1 terrain, 2 glissieres, 3 tunnel, 4 sol studio
in vec3 in_pos;                 // x = parametre lateral, y = hauteur profil, z = profondeur
out vec3 v_pos; out vec2 v_p; out vec3 v_n;

float terrainH(float x, float s){
    float ax = abs(x) - 9.2;
    if(ax <= 0.) return 0.;
    if(ENV==1) return -.15*min(ax,1.) + smoothstep(0.,60.,ax)*(fbm(vec2(x*.018+9., s*.015))*15.-3.5) + fbm(vec2(x,s)*.11)*.8*smoothstep(0.,8.,ax) + smoothstep(90.,240.,ax)*28.*fbm(vec2(x*.008,s*.006));
    if(ENV==3){
        float nse = fbm(vec2(x*.045+3., s*.032));
        if(x < 0.) return smoothstep(0.,9.,ax)*(2.+nse*3.) + pow(smoothstep(2.,90.,ax),1.1)*(34.+46.*fbm(vec2(x*.02,s*.012)));
        return -smoothstep(1.,30.,ax)*(5.+16.*nse) - smoothstep(20.,120.,ax)*16. + smoothstep(150.,260.,ax)*46.*fbm(vec2(x*.01,s*.008));
    }
    return -.10*min(ax,1.);
}
void main(){
    vec3 w = in_pos; v_n = vec3(0,1,0); v_p = vec2(in_pos.x, in_pos.y);
    if(u_part==1){
        float a = in_pos.x, sgn = sign(a); a = abs(a);
        w.x = sgn * (8.9 + 271. * a*a*(.25+.75*a));
        w.z = in_pos.z - mod(u_track.x, 5.);
        float s = u_track.x + w.z;
        w.y = terrainH(w.x, s);
        float e = 1.6;
        v_n = normalize(vec3(terrainH(w.x-e,s)-terrainH(w.x+e,s), 2.*e, terrainH(w.x,s-e)-terrainH(w.x,s+e)));
    } else if(u_part==3){
        float a = in_pos.x * PI;
        vec2 q = vec2(cos(a), sin(a));
        q = sign(q)*pow(abs(q), vec2(.62));
        w.x = q.x * 10.6; w.y = q.y * 7.6 - .05;
        v_n = vec3(-q.x, -q.y, 0.);
    } else if(u_part==2){
        v_n = vec3(-sign(in_pos.x), .35, 0.);
    }
    v_pos = w;
    vec2 b = u_part==4 ? vec2(0.) : texture(u_bend, vec2((w.z + 30.) / u_track.z, .5)).xy;
    vec3 q3 = w; q3.y *= u_track.w; q3.xy += b;
    gl_Position = u_vp * vec4(q3, 1.);
    gl_ClipDistance[0] = u_track.w < 0. ? w.y - .02 : 1.;
}
