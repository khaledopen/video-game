in vec2 v_uv; in vec4 v_col; flat in int v_kind; in vec3 v_pos;
out vec4 frag;          // premultiplie : rgb additif, a occultation
void main(){
    float fog = exp(-pow(length(v_pos-u_cam.xyz)*u_fog.w,1.45));
    if(v_kind==0){                                   // ombre de contact
        vec2 q = abs(v_uv); float d = length(max(q-vec2(.45,.62),0.)/vec2(.55,.38));
        float a = smoothstep(1.,.0,d);
        frag = vec4(0.,0.,0., a*v_col.a*fog); return;
    }
    if(v_kind==1){                                   // neon sous caisse
        vec2 q = abs(v_uv); float d = length(max(q-vec2(.42,.55),0.)/vec2(.58,.45));
        float a = pow(smoothstep(1.,.0,d), 2.2);
        frag = vec4(v_col.rgb*a*fog, 0.); return;
    }
    if(v_kind==2){                                   // flaque
        float r = length(v_uv) + .16*sin(atan(v_uv.y,v_uv.x)*3.+v_col.a*40.) + .08*sin(atan(v_uv.y,v_uv.x)*7.+v_col.a*9.);
        float a = smoothstep(.96,.84,r);
        vec3 v = normalize(u_cam.xyz - v_pos); float fr = pow(1.-max(v.y,0.),3.);
        float rp = noise(v_uv*9. + vec2(u_cam.w*1.4,-u_cam.w));
        vec3 sky = skyBase(reflect(-v, normalize(vec3((rp-.5)*.25,1.,(rp-.5)*.2))))*1.4 + v_col.rgb*.30;
        float rim = smoothstep(.10,.0,abs(r-.88));
        frag = vec4((sky*(.35+.65*fr) + vec3(.10,.35,.55)*rim*.6)*a*fog, a*.80*fog); return;
    }
    if(v_kind==3){                                   // trace lumineuse allongee derriere les feux
        float a = pow(1.-abs(v_uv.x),2.)*pow(clamp(v_uv.y*.5+.5,0.,1.),2.);
        frag = vec4(v_col.rgb*a*fog,0.); return;
    }
    if(v_kind==4){                                   // anneau (bouclier, portail)
        float r = length(v_uv);
        float a = smoothstep(.08,.0,abs(r-.86)) + .25*smoothstep(1.,.2,r);
        frag = vec4(v_col.rgb*a*fog,0.); return;
    }
    if(v_kind==5){                                   // zone de travaux hachuree
        float h = step(.5, fract((v_uv.x + v_uv.y*2.2)*2.5));
        float e = smoothstep(1.,.96,max(abs(v_uv.x),abs(v_uv.y)));
        frag = vec4(mix(vec3(.02),vec3(.75,.38,.02),h)*e*.35*fog, .55*e*fog); return;
    }
    float r = length(v_uv);                          // halo simple
    frag = vec4(v_col.rgb*pow(max(1.-r,0.),2.)*fog,0.);
}